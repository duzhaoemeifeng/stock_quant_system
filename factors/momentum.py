"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
动量类因子：变化率、动量、资金流量指数。
"""

import pandas as pd

from .base import Factor
from .registry import FactorRegistry


@FactorRegistry.register
class RateOfChangeFactor(Factor):
    """价格变化率 Rate of Change。

    params:
        window: 回看周期（默认 12）。
        column: 计算列（默认 "close"）。

    Formula: (close[t] / close[t-window] - 1) * 100
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 12)
        self.column = self.params.get("column", "close")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        series = data[self.column].astype(float)
        roc = (series / series.shift(self.window) - 1.0) * 100.0
        return roc


@FactorRegistry.register
class MomentumFactor(Factor):
    """价格动量 Momentum。

    params:
        window: 回看周期（默认 10）。
        column: 计算列（默认 "close"）。

    Formula: close[t] - close[t-window]
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 10)
        self.column = self.params.get("column", "close")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        series = data[self.column].astype(float)
        return series - series.shift(self.window)


@FactorRegistry.register
class RelativeStrengthFactor(Factor):
    """相对强弱（价格 / N日前价格 - 1）。

    params:
        window: 回看周期（默认 20）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        return close / close.shift(self.window) - 1.0
