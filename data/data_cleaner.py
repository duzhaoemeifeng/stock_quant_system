"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。数据清洗无法消除所有数据偏差，
 清洗后的数据仍可能包含未被检测到的异常。
==================================================
数据清洗模块：缺失值处理、异常价格剔除、交易日历补齐。
"""

import numpy as np
import pandas as pd

from .base import Col


class DataCleaner:
    """数据清洗工具。

    提供静态方法对统一 Schema 的 OHLCV DataFrame 进行清洗。
    所有方法均返回新的 DataFrame，不修改原数据。

    使用方法:
        cleaner = DataCleaner()
        df_clean = cleaner.pipeline(raw_df)
    """

    # ---- 清洗管线 ----

    def pipeline(
        self,
        df: pd.DataFrame,
        max_gap: int = 3,
        zscore_threshold: float = 5.0,
        min_price: float = 0.01,
    ) -> pd.DataFrame:
        """执行完整的清洗管线。

        Args:
            df: 统一 Schema DataFrame。
            max_gap: 前向填充最大连续缺失天数。
            zscore_threshold: 涨跌幅 Z-score 异常阈值。
            min_price: 最低有效价格。

        Returns:
            清洗后的 DataFrame。
        """
        df = df.copy()
        df = self.forward_fill_ohlcv(df, max_gap=max_gap)
        df = self.remove_price_anomalies(df, min_price=min_price)
        if Col.PCT_CHG in df.columns:
            df = self.remove_outliers_by_zscore(
                df, column=Col.PCT_CHG, threshold=zscore_threshold
            )
        return df

    # ---- 子步骤 ----

    @staticmethod
    def forward_fill_ohlcv(
        df: pd.DataFrame, max_gap: int = 3
    ) -> pd.DataFrame:
        """前向填充 OHLCV 缺失值。

        仅填充连续缺失不超过 max_gap 个交易日的缺口。
        超过该天数的缺口保留 NaN（停牌等情况）。

        Args:
            df: 统一 Schema DataFrame。
            max_gap: 最大连续填充天数。

        Returns:
            填充后的 DataFrame。
        """
        df = df.sort_index()
        ohlcv_cols = [Col.OPEN, Col.HIGH, Col.LOW, Col.CLOSE, Col.VOLUME]
        available = [c for c in ohlcv_cols if c in df.columns]

        for col in available:
            df[col] = df[col].ffill(limit=max_gap)

        return df

    @staticmethod
    def remove_outliers_by_zscore(
        df: pd.DataFrame,
        column: str = Col.PCT_CHG,
        threshold: float = 5.0,
    ) -> pd.DataFrame:
        """基于 Z-score 移除单日涨跌幅异常值。

        常用于去除数据源错误导致的极端涨跌幅记录。

        Args:
            df: 统一 Schema DataFrame。
            column: 待检测列名。
            threshold: Z-score 阈值，超过则标记为 NaN。

        Returns:
            异常值被置为 NaN 的 DataFrame。
        """
        if column not in df.columns:
            return df

        series = df[column].dropna()
        if len(series) < 10:
            return df

        z_scores = np.abs(
            (series - series.mean()) / (series.std() + 1e-12)
        )
        mask = z_scores > threshold
        df.loc[series[mask].index, column] = np.nan
        return df

    @staticmethod
    def remove_price_anomalies(
        df: pd.DataFrame,
        min_price: float = 0.01,
        max_price_mult: float = 100.0,
    ) -> pd.DataFrame:
        """移除价格异常记录。

        检测条件：
        - 价格 <= min_price（负价或零价）
        - 价格超过同列中位数的 max_price_mult 倍

        Args:
            df: 统一 Schema DataFrame。
            min_price: 最低有效价格。
            max_price_mult: 相对中位数的最大倍数。

        Returns:
            异常数据被置为 NaN 的 DataFrame。
        """
        price_cols = [Col.OPEN, Col.HIGH, Col.LOW, Col.CLOSE]
        available = [c for c in price_cols if c in df.columns]

        for col in available:
            series = df[col]
            median_price = series.median()

            # 移除负价/零价
            mask_zero = series <= min_price
            df.loc[mask_zero[mask_zero].index, col] = np.nan

            # 移除远超中位数的价格
            if median_price > 0:
                mask_extreme = series > median_price * max_price_mult
                df.loc[mask_extreme[mask_extreme].index, col] = np.nan

        return df

    @staticmethod
    def fill_trading_calendar(
        df: pd.DataFrame,
        calendar: list[pd.Timestamp],
    ) -> pd.DataFrame:
        """补齐交易日历中缺失的日期。

        对停牌日填充 NaN，确保回测时日期连续。

        Args:
            df: 统一 Schema DataFrame，日期索引。
            calendar: 完整交易日历列表。

        Returns:
            按日历 reindex 后的 DataFrame。
        """
        df = df.sort_index()
        df = df.reindex(calendar)
        return df
