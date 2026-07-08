"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
特征工程 — 从 OHLCV 数据构造 35 维 ML 特征。
"""

import numpy as np
import pandas as pd


class FeatureEngineer:
    """从 OHLCV 数据构造预测特征。

    特征类别（约 35 维）:
    - 价格回报: return_1d, return_5d, return_10d, return_20d, log_return_1d
    - 日内形态: high_low_pct, close_open_pct
    - 均线位置: close_sma_5, close_sma_10, close_sma_20, close_sma_60
    - 技术指标: rsi_14, macd, macd_signal, macd_hist, bb_pct_b, bb_width, atr_norm
    - 动量: roc_5, roc_10, roc_20
    - 波动率: hist_vol_20, hist_vol_60, atr_ratio
    - 成交量: volume_change_1d, volume_ratio_5, volume_ratio_20
    - 趋势: adx_14, plus_di, minus_di
    """

    FEATURE_COLS: list[str] = []  # 由 compute_features 动态设置

    # ---- 价格回报 ----

    @staticmethod
    def _return_1d(close: pd.Series) -> pd.Series:
        return close.pct_change(1)

    @staticmethod
    def _return_5d(close: pd.Series) -> pd.Series:
        return close.pct_change(5)

    @staticmethod
    def _return_10d(close: pd.Series) -> pd.Series:
        return close.pct_change(10)

    @staticmethod
    def _return_20d(close: pd.Series) -> pd.Series:
        return close.pct_change(20)

    @staticmethod
    def _log_return_1d(close: pd.Series) -> pd.Series:
        return np.log(close / close.shift(1))

    # ---- 日内形态 ----

    @staticmethod
    def _high_low_pct(data: pd.DataFrame) -> pd.Series:
        return (data["high"] - data["low"]) / data["close"] * 100

    @staticmethod
    def _close_open_pct(data: pd.DataFrame) -> pd.Series:
        return (data["close"] - data["open"]) / data["open"] * 100

    # ---- 均线位置 ----

    @staticmethod
    def _close_sma(close: pd.Series, window: int) -> pd.Series:
        sma = close.rolling(window=window, min_periods=window).mean()
        return close / sma - 1

    @staticmethod
    def _sma_value(close: pd.Series, window: int) -> pd.Series:
        return close.rolling(window=window, min_periods=window).mean()

    # ---- RSI ----

    @staticmethod
    def _rsi(close: pd.Series, window: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
        loss = (-delta).clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
        rs = gain / (loss + 1e-12)
        return 100 - 100 / (1 + rs)

    # ---- MACD ----

    @staticmethod
    def _macd_values(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        hist = macd_line - signal_line
        return macd_line, signal_line, hist

    # ---- 布林带 ----

    @staticmethod
    def _bollinger(close: pd.Series, window: int = 20, n_std: int = 2) -> tuple[pd.Series, pd.Series]:
        sma = close.rolling(window=window, min_periods=window).mean()
        std = close.rolling(window=window, min_periods=window).std()
        upper = sma + n_std * std
        lower = sma - n_std * std
        pct_b = (close - lower) / (upper - lower + 1e-12)
        bandwidth = (upper - lower) / (sma + 1e-12) * 100
        return pct_b, bandwidth

    # ---- ATR ----

    @staticmethod
    def _atr(data: pd.DataFrame, window: int = 14) -> pd.Series:
        high, low, close = data["high"], data["low"], data["close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / window, adjust=False).mean()

    # ---- 历史波动率 ----

    @staticmethod
    def _hist_vol(close: pd.Series, window: int, periods_per_year: int = 252) -> pd.Series:
        log_ret = np.log(close / close.shift(1))
        return log_ret.rolling(window=window, min_periods=window).std() * np.sqrt(periods_per_year)

    # ---- ADX ----

    @staticmethod
    def _adx_di(data: pd.DataFrame, window: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
        high, low, close = data["high"], data["low"], data["close"]
        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        atr = FeatureEngineer._atr(data, window)
        plus_di = pd.Series(
            100 * pd.Series(plus_dm, index=data.index).ewm(alpha=1 / window, adjust=False).mean() / atr,
            index=data.index,
        )
        minus_di = pd.Series(
            100 * pd.Series(minus_dm, index=data.index).ewm(alpha=1 / window, adjust=False).mean() / atr,
            index=data.index,
        )

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12)
        adx = dx.ewm(alpha=1 / window, adjust=False).mean()
        return adx, plus_di, minus_di

    # ---- 主方法 ----

    def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """从 OHLCV 数据计算特征矩阵。

        Args:
            data: DataFrame with columns [open, high, low, close, volume]

        Returns:
            DataFrame of features, 与 data 等行数
        """
        close = data["close"].astype(float)

        features = pd.DataFrame(index=data.index)

        # 价格回报 (5)
        features["return_1d"] = self._return_1d(close)
        features["return_5d"] = self._return_5d(close)
        features["return_10d"] = self._return_10d(close)
        features["return_20d"] = self._return_20d(close)
        features["log_return_1d"] = self._log_return_1d(close)

        # 日内形态 (2)
        features["high_low_pct"] = self._high_low_pct(data)
        features["close_open_pct"] = self._close_open_pct(data)

        # 均线位置 (4)
        features["close_sma_5"] = self._close_sma(close, 5)
        features["close_sma_10"] = self._close_sma(close, 10)
        features["close_sma_20"] = self._close_sma(close, 20)
        features["close_sma_60"] = self._close_sma(close, 60)

        # 技术指标: RSI (1)
        features["rsi_14"] = self._rsi(close, 14)

        # 技术指标: MACD (3)
        macd_line, macd_signal, macd_hist = self._macd_values(close)
        features["macd"] = macd_line
        features["macd_signal"] = macd_signal
        features["macd_hist"] = macd_hist

        # 技术指标: 布林带 (2)
        bb_pct_b, bb_width = self._bollinger(close)
        features["bb_pct_b"] = bb_pct_b
        features["bb_width"] = bb_width

        # 技术指标: ATR 归一化 (1)
        atr = self._atr(data, 14)
        features["atr_norm"] = atr / close * 100

        # 动量 (3)
        features["roc_5"] = close.pct_change(5) * 100
        features["roc_10"] = close.pct_change(10) * 100
        features["roc_20"] = close.pct_change(20) * 100

        # 波动率 (3)
        features["hist_vol_20"] = self._hist_vol(close, 20)
        features["hist_vol_60"] = self._hist_vol(close, 60)
        features["atr_ratio"] = atr / close

        # 成交量 (3)
        features["volume_change_1d"] = data["volume"].pct_change(1)
        features["volume_ratio_5"] = data["volume"] / data["volume"].rolling(5, min_periods=5).mean()
        features["volume_ratio_20"] = data["volume"] / data["volume"].rolling(20, min_periods=20).mean()

        # 趋势强度 (3)
        adx, plus_di, minus_di = self._adx_di(data, 14)
        features["adx_14"] = adx
        features["plus_di"] = plus_di
        features["minus_di"] = minus_di

        # ---- 比值特征 (2) ----
        features["di_ratio"] = plus_di / (minus_di + 1e-12)
        features["macd_ratio"] = macd_hist / (close + 1e-12) * 1000

        # 记录特征列名
        self.FEATURE_COLS = list(features.columns)

        return features

    def compute_target(self, data: pd.DataFrame, horizon: int = 1) -> pd.Series:
        """计算分类目标：次日涨跌。

        Args:
            data: OHLCV DataFrame
            horizon: 预测周期（默认1天）

        Returns:
            Series: 1=上涨, 0=下跌，最后 horizon 行为 NaN
        """
        close = data["close"].astype(float)
        future_return = close.shift(-horizon) / close - 1
        target = (future_return > 0).astype(float)
        target.iloc[-horizon:] = np.nan
        return target

    def compute_target_regression(self, data: pd.DataFrame, horizon: int = 1) -> pd.Series:
        """计算回归目标：次日收益率。

        Args:
            data: OHLCV DataFrame
            horizon: 预测周期

        Returns:
            Series of returns，最后 horizon 行为 NaN
        """
        close = data["close"].astype(float)
        result = close.shift(-horizon) / close - 1
        return result  # shift(-horizon) naturally produces NaN at the end
