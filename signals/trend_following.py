"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。趋势跟踪策略在震荡市中
 可能产生频繁假信号，导致持续亏损。
==================================================
趋势跟踪信号生成器：双均线交叉、MACD 金叉死叉。
"""

import pandas as pd

from .base import SignalGenerator
from ..factors.technical import SMAFactor, MACDFactor


class DualMACrossoverSignal(SignalGenerator):
    """双均线交叉信号。

    params:
        fast_window: 快线周期（默认 5）。
        slow_window: 慢线周期（默认 20）。
        column: 计算列（默认 "close"）。

    快线上穿慢线 → 买入 (+1)
    快线下穿慢线 → 卖出 (-1)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.fast_window = self.params.get("fast_window", 5)
        self.slow_window = self.params.get("slow_window", 20)
        self.column = self.params.get("column", "close")

    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        sma_fast = SMAFactor({"window": self.fast_window, "column": self.column})
        sma_slow = SMAFactor({"window": self.slow_window, "column": self.column})

        fast_ma = sma_fast.compute(data)
        slow_ma = sma_slow.compute(data)

        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        signals.loc[fast_ma > slow_ma, "signal"] = 1
        signals.loc[fast_ma < slow_ma, "signal"] = -1

        # 交叉发生时产生交易信号
        signals["signal"] = signals["signal"].diff().fillna(0)
        # 仅保留交叉点
        signals.loc[signals["signal"] == 0, "signal"] = float("nan")

        # 信号强度：价格距离均线的标准化距离
        spread = ((fast_ma - slow_ma) / (slow_ma + 1e-12)).abs()
        max_spread = spread.rolling(window=252, min_periods=20).max()
        signals["signal_strength"] = (spread / (max_spread + 1e-12)).clip(0, 1)

        return signals


class MACDSignalGenerator(SignalGenerator):
    """MACD 信号生成器。

    params:
        fast: 快线周期（默认 12）。
        slow: 慢线周期（默认 26）。
        signal_period: 信号线周期（默认 9）。

    MACD 上穿信号线 → 买入 (+1)
    MACD 下穿信号线 → 卖出 (-1)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.fast = self.params.get("fast", 12)
        self.slow = self.params.get("slow", 26)
        self.signal_period = self.params.get("signal_period", 9)

    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        macd = MACDFactor({
            "fast": self.fast,
            "slow": self.slow,
            "signal": self.signal_period,
        })
        result = macd.compute(data)
        macd_line = result["macd"]
        signal_line = result["macd_signal"]

        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        signals.loc[macd_line > signal_line, "signal"] = 1
        signals.loc[macd_line < signal_line, "signal"] = -1

        # 交叉点
        signals["signal"] = signals["signal"].diff().fillna(0)
        signals.loc[signals["signal"] == 0, "signal"] = float("nan")

        # 强度：直方图绝对值 / 收盘价
        histogram = result["macd_histogram"]
        signals["signal_strength"] = (
            histogram.abs() / (data["close"] + 1e-12)
        ).clip(0, 1)

        return signals
