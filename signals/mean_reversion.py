"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。均值回归策略在强趋势行情中
 可能面临"接飞刀"风险，导致大幅亏损。
==================================================
均值回归信号生成器：RSI 超买超卖、布林带回归。
"""

import pandas as pd

from .base import SignalGenerator
from ..factors.technical import RSIFactor, BollingerFactor


class RSIReversalSignal(SignalGenerator):
    """RSI 超买超卖反转信号。

    params:
        window: RSI 周期（默认 14）。
        oversold: 超卖阈值（默认 30）。
        overbought: 超买阈值（默认 70）。

    RSI 从下方突破 oversold → 买入 (+1)
    RSI 从上方跌破 overbought → 卖出 (-1)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.window = self.params.get("window", 14)
        self.oversold = self.params.get("oversold", 30)
        self.overbought = self.params.get("overbought", 70)

    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        rsi = RSIFactor({"window": self.window}).compute(data)

        signals = pd.DataFrame(index=data.index)
        signals["signal"] = float("nan")

        # 超卖区域 → 准备买入
        oversold_zone = rsi < self.oversold
        # 超买区域 → 准备卖出
        overbought_zone = rsi > self.overbought

        # 从超卖区回升 → 买入
        exit_oversold = oversold_zone.shift(1).fillna(False) & (~oversold_zone)
        signals.loc[exit_oversold, "signal"] = 1

        # 从超买区回落 → 卖出
        exit_overbought = overbought_zone.shift(1).fillna(False) & (~overbought_zone)
        signals.loc[exit_overbought, "signal"] = -1

        # 信号强度：RSI 偏离中值的归一化距离
        signals["signal_strength"] = (abs(rsi - 50) / 50).clip(0, 1)

        return signals


class BollingerReversalSignal(SignalGenerator):
    """布林带均值回归信号。

    params:
        window: 布林带周期（默认 20）。
        num_std: 标准差倍数（默认 2.0）。

    价格触及下轨后回升 → 买入 (+1)
    价格触及上轨后回落 → 卖出 (-1)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.window = self.params.get("window", 20)
        self.num_std = self.params.get("num_std", 2.0)

    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        boll = BollingerFactor({
            "window": self.window,
            "num_std": self.num_std,
        })
        result = boll.compute(data)
        close = data["close"]
        lower = result["boll_lower"]
        upper = result["boll_upper"]

        signals = pd.DataFrame(index=data.index)
        signals["signal"] = float("nan")

        # 价格低于下轨 → 超卖
        below_lower = close < lower
        # 价格高于上轨 → 超买
        above_upper = close > upper

        # 从下轨下方回到下轨上方 → 买入
        signals.loc[
            below_lower.shift(1).fillna(False) & (~below_lower), "signal"
        ] = 1

        # 从上轨上方回到上轨下方 → 卖出
        signals.loc[
            above_upper.shift(1).fillna(False) & (~above_upper), "signal"
        ] = -1

        # 信号强度：%b 偏离中值
        pct_b = result["boll_pct_b"]
        signals["signal_strength"] = (abs(pct_b - 0.5) * 2).clip(0, 1)

        return signals
