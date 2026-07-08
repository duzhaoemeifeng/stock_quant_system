"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。过滤条件可能同时滤除有效信号，
 过度过滤会导致策略欠拟合。
==================================================
信号过滤链：组合多个条件过滤器，支持 AND/OR 逻辑。
"""

from typing import Callable

import pandas as pd


class FilterChain:
    """信号过滤链。

    对生成的信号施加多条件过滤，过滤掉的信号置为 NaN。
    支持 AND / OR / NOT 逻辑组合。

    使用方法:
        chain = FilterChain(mode="AND")
        chain.add_filter("min_volume", lambda s, d: d["volume"] > 1_000_000)
        chain.add_filter("high_volatility", my_vol_filter)
        filtered = chain.apply(signal_df, data)
    """

    def __init__(self, mode: str = "AND"):
        """
        Args:
            mode: 过滤逻辑 "AND" | "OR"。
        """
        if mode not in ("AND", "OR"):
            raise ValueError(f"mode 必须是 'AND' 或 'OR'，实际: {mode}")
        self.mode = mode
        self._filters: list[tuple[str, Callable]] = []

    def add_filter(
        self, name: str, filter_fn: Callable
    ) -> "FilterChain":
        """添加一条过滤规则。

        Args:
            name: 过滤规则名称。
            filter_fn: 可调用对象，签名 (signal_df, data_df) -> bool Series。

        Returns:
            self（链式调用）。
        """
        self._filters.append((name, filter_fn))
        return self

    def apply(
        self,
        signals: pd.DataFrame,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """应用所有过滤规则。

        Args:
            signals: 信号 DataFrame，必须包含 'signal' 列。
            data: 原始 OHLCV 数据。

        Returns:
            过滤后的信号 DataFrame。
        """
        if not self._filters:
            return signals

        result = signals.copy()
        signal_col = "signal" if "signal" in result.columns else result.columns[0]
        has_signal = result[signal_col].notna()

        # 收集所有过滤条件的结果
        filter_results = []
        for name, fn in self._filters:
            try:
                mask = fn(signals, data)
                # mask 可能返回 Series 或标量
                if not isinstance(mask, pd.Series):
                    mask = pd.Series(mask, index=signals.index)
                filter_results.append((name, mask))
            except Exception:
                # 过滤规则出错时跳过（不阻塞管线）
                continue

        if not filter_results:
            return result

        if self.mode == "AND":
            # 所有条件必须同时满足
            combined = pd.Series(True, index=signals.index)
            for _, mask in filter_results:
                combined = combined & mask.fillna(False)
        else:
            # 任一条件满足即可
            combined = pd.Series(False, index=signals.index)
            for _, mask in filter_results:
                combined = combined | mask.fillna(False)

        # 只保留满足条件的信号
        valid = combined.reindex(signals.index).fillna(False)
        result.loc[has_signal & ~valid, signal_col] = float("nan")
        return result

    @property
    def filter_names(self) -> list[str]:
        """返回所有过滤规则名称。"""
        return [name for name, _ in self._filters]


# ============================================================
#  内置过滤函数
# ============================================================

def min_volume_filter(threshold: float = 1_000_000):
    """最低成交量过滤：成交量 < threshold 时过滤。"""
    return lambda signals, data: data["volume"] > threshold


def min_price_filter(threshold: float = 1.0):
    """最低价格过滤：收盘价 < threshold 时过滤（过滤低价股）。"""
    return lambda signals, data: data["close"] > threshold


def volatility_filter(max_annual_vol: float = 0.60):
    """波动率过滤：年化波动率 > max_annual_vol 时过滤。

    年化波动率 > 60% 通常意味着极端行情，暂停交易。
    """
    def _filter(signals, data):
        log_ret = data["close"].pct_change()
        vol = log_ret.rolling(20).std() * (252 ** 0.5)
        return vol < max_annual_vol
    return _filter


def min_bars_between_trades(min_bars: int = 5):
    """最小交易间隔过滤：两次信号之间至少间隔 min_bars 根K线。"""
    def _filter(signals, data):
        signal_col = "signal" if "signal" in signals.columns else signals.columns[0]
        trade_mask = signals[signal_col].notna()
        if not trade_mask.any():
            return pd.Series(True, index=signals.index)
        # 标记前 min_bars 根K线内是否已有信号
        valid = pd.Series(True, index=signals.index)
        trade_dates = signals.index[trade_mask]
        for dt in trade_dates:
            pos = signals.index.get_loc(dt)
            start = max(0, pos - min_bars)
            end = min(len(signals.index), pos + min_bars + 1)
            valid.iloc[start:end] = False
            valid.iloc[pos] = True  # 当前信号保留
        return valid
    return _filter
