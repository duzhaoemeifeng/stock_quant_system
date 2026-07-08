"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。技术指标仅反映历史价格统计特征，
 不可作为唯一交易决策依据。
==================================================
标准技术指标因子：均线、MACD、RSI、布林带、ATR。
"""

import numpy as np
import pandas as pd

from .base import Factor
from .registry import FactorRegistry


def _get_column(data: pd.DataFrame, column: str = "close") -> pd.Series:
    """安全获取列数据。"""
    col_map = {
        "close": "close", "open": "open", "high": "high",
        "low": "low", "volume": "volume", "amount": "amount",
        "hlc3": None, "hl2": None, "ohlc4": None,
    }
    col = col_map.get(column, "close")
    if col and col in data.columns:
        return data[col].astype(float)

    # 典型价格计算
    if column == "hlc3":
        return (data["high"] + data["low"] + data["close"]) / 3.0
    if column == "hl2":
        return (data["high"] + data["low"]) / 2.0
    if column == "ohlc4":
        return (data["open"] + data["high"] + data["low"] + data["close"]) / 4.0

    return data["close"].astype(float)


@FactorRegistry.register
class SMAFactor(Factor):
    """简单移动均线 Simple Moving Average。

    params:
        window: 计算窗口（默认 20）。
        column: 计算列（默认 "close"）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)
        self.column = self.params.get("column", "close")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        series = _get_column(data, self.column)
        return series.rolling(window=self.window, min_periods=self.window).mean()


@FactorRegistry.register
class EMAFactor(Factor):
    """指数移动均线 Exponential Moving Average。

    params:
        window: 计算窗口（默认 20）。
        column: 计算列（默认 "close"）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)
        self.column = self.params.get("column", "close")

    def compute(self, data: pd.DataFrame) -> pd.Series:
        series = _get_column(data, self.column)
        return series.ewm(span=self.window, adjust=False).mean()


@FactorRegistry.register
class MACDFactor(Factor):
    """MACD 指标。

    params:
        fast: 快线周期（默认 12）。
        slow: 慢线周期（默认 26）。
        signal: 信号线周期（默认 9）。

    Returns:
        DataFrame with columns: macd, signal, histogram
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.fast = self.params.get("fast", 12)
        self.slow = self.params.get("slow", 26)
        self.signal_period = self.params.get("signal", 9)

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"].astype(float)
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame({
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
        }, index=data.index)


@FactorRegistry.register
class RSIFactor(Factor):
    """相对强弱指数 RSI。

    params:
        window: 计算窗口（默认 14）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 14)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1.0 / self.window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / self.window, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-12)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi


@FactorRegistry.register
class BollingerFactor(Factor):
    """布林带 Bollinger Bands。

    params:
        window: 均线窗口（默认 20）。
        num_std: 标准差倍数（默认 2.0）。

    Returns:
        DataFrame with columns: boll_upper, boll_middle, boll_lower, boll_pct_b, boll_bandwidth
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)
        self.num_std = self.params.get("num_std", 2.0)

    def compute(self, data: pd.DataFrame) -> pd.DataFrame:
        close = data["close"].astype(float)
        middle = close.rolling(window=self.window, min_periods=self.window).mean()
        std = close.rolling(window=self.window, min_periods=self.window).std()
        upper = middle + self.num_std * std
        lower = middle - self.num_std * std
        pct_b = (close - lower) / (upper - lower + 1e-12)
        bandwidth = (upper - lower) / (middle + 1e-12)
        return pd.DataFrame({
            "boll_upper": upper,
            "boll_middle": middle,
            "boll_lower": lower,
            "boll_pct_b": pct_b,
            "boll_bandwidth": bandwidth,
        }, index=data.index)


@FactorRegistry.register
class ATRFactor(Factor):
    """平均真实波幅 Average True Range。

    params:
        window: 计算窗口（默认 14）。
        normalize: 是否除以收盘价做归一化（默认 False）。
    """

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 14)
        self.normalize = self.params.get("normalize", False)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        close = data["close"].astype(float)
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = true_range.ewm(alpha=1.0 / self.window, adjust=False).mean()

        if self.normalize:
            atr = atr / (close + 1e-12) * 100.0

        return atr
