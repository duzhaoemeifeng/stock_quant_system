"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
波动率类因子：历史波动率、归一化 ATR。
"""

import numpy as np
import pandas as pd

from .base import Factor
from .registry import FactorRegistry


@FactorRegistry.register
class HistoricalVolatilityFactor(Factor):
    """历史波动率 Historical Volatility。

    params:
        window: 计算窗口（默认 20）。
        annualize: 是否年化（默认 True，交易日按 252 折算）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)
        self.annualize = self.params.get("annualize", True)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        log_returns = np.log(close / close.shift(1))
        vol = log_returns.rolling(window=self.window, min_periods=5).std()
        if self.annualize:
            vol = vol * np.sqrt(252)
        return vol


@FactorRegistry.register
class DailyReturnFactor(Factor):
    """日收益率因子。

    params:
        log_return: 是否使用对数收益率（默认 False，使用百分比）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.log_return = self.params.get("log_return", False)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        if self.log_return:
            return np.log(close / close.shift(1))
        return close.pct_change()


@FactorRegistry.register
class VolumeWeightedPriceFactor(Factor):
    """量价加权因子：成交量 * 收盘价 / N日均量（近似 VWAP 偏离度）。

    params:
        window: 均量周期（默认 20）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        volume = data["volume"].astype(float)
        avg_volume = volume.rolling(window=self.window, min_periods=5).mean()
        vwap_approx = (close * volume).rolling(window=self.window).sum() / (
            volume.rolling(window=self.window).sum() + 1e-12
        )
        deviation = (close - vwap_approx) / (vwap_approx + 1e-12)
        return deviation
