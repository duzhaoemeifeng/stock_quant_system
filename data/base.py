"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
数据源抽象基类与统一 DataFrame Schema 定义。
"""

from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


# ============================================================
#  统一 Schema 列名常量
# ============================================================

class Col(str, Enum):
    """统一 DataFrame 列名枚举。

    所有数据源（AKShare、yfinance 等）输出的 DataFrame
    均使用此标准列名，上层模块无需感知数据源差异。
    """
    SYMBOL = "symbol"
    DATE = "date"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    AMOUNT = "amount"
    ADJ_CLOSE = "adj_close"
    PCT_CHG = "pct_chg"
    TURNOVER = "turnover"


# 统一 Schema 的必需列
REQUIRED_COLUMNS: list[str] = [
    Col.SYMBOL, Col.DATE, Col.OPEN, Col.HIGH,
    Col.LOW, Col.CLOSE, Col.VOLUME,
]

# AKShare -> 统一 Schema 列名映射
AKSHARE_COLUMN_MAP: dict[str, str] = {
    "日期": Col.DATE,
    "开盘": Col.OPEN,
    "最高": Col.HIGH,
    "最低": Col.LOW,
    "收盘": Col.CLOSE,
    "成交量": Col.VOLUME,
    "成交额": Col.AMOUNT,
    "涨跌幅": Col.PCT_CHG,
    "换手率": Col.TURNOVER,
}

# yfinance -> 统一 Schema 列名映射
YFINANCE_COLUMN_MAP: dict[str, str] = {
    "Open": Col.OPEN,
    "High": Col.HIGH,
    "Low": Col.LOW,
    "Close": Col.CLOSE,
    "Volume": Col.VOLUME,
    "Adj Close": Col.ADJ_CLOSE,
}


def apply_schema(
    df: pd.DataFrame,
    source: str = "akshare",
    symbol: str = "",
) -> pd.DataFrame:
    """将原始 DataFrame 转换为统一 Schema。

    Args:
        df: 数据源原始 DataFrame。
        source: 数据源标识 "akshare" | "yfinance"。
        symbol: 股票代码。

    Returns:
        符合统一 Schema 的 DataFrame，按日期排序。
    """
    if df.empty:
        return _empty_schema_df()

    df = df.copy()

    if source == "akshare":
        col_map = AKSHARE_COLUMN_MAP
    elif source == "yfinance":
        col_map = YFINANCE_COLUMN_MAP
    else:
        raise ValueError(f"不支持的数据源: {source}")

    df.rename(columns=col_map, inplace=True)

    # 确保 symbol 列
    if Col.SYMBOL not in df.columns:
        df[Col.SYMBOL] = symbol

    # 确保 date 列为 datetime
    if Col.DATE in df.columns:
        df[Col.DATE] = pd.to_datetime(df[Col.DATE], errors="coerce")
        df.set_index(Col.DATE, inplace=True)
    elif df.index.name == Col.DATE or isinstance(df.index, pd.DatetimeIndex):
        pass
    else:
        # 尝试把 index 转为 datetime
        df.index = pd.to_datetime(df.index, errors="coerce")

    # 数值列类型转换
    numeric_cols = [Col.OPEN, Col.HIGH, Col.LOW, Col.CLOSE,
                    Col.VOLUME, Col.AMOUNT, Col.PCT_CHG]
    for c in numeric_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # 只保留需要的列
    keep_cols = [c for c in REQUIRED_COLUMNS + [Col.AMOUNT, Col.PCT_CHG, Col.ADJ_CLOSE, Col.TURNOVER]
                 if c in df.columns]
    df = df[keep_cols].sort_index()

    return df


def _empty_schema_df() -> pd.DataFrame:
    """返回空的统一 Schema DataFrame。"""
    return pd.DataFrame(columns=REQUIRED_COLUMNS)


def validate_schema(df: pd.DataFrame) -> bool:
    """校验 DataFrame 是否满足统一 Schema 要求。

    Args:
        df: 待校验 DataFrame。

    Returns:
        是否通过校验。

    Raises:
        ValueError: 缺失必需列。
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame 缺失必需列: {missing}")
    return True


# ============================================================
#  DataSource 抽象基类
# ============================================================

class DataSource(ABC):
    """所有数据源的抽象基类。

    风险提示：数据来源于公开免费接口，可能存在延迟或缺失，
    不可作为唯一决策依据。
    """

    @abstractmethod
    def download_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """下载日线K线数据。

        Args:
            symbol: 股票代码。
            start_date: 起始日期 "YYYYMMDD"。
            end_date: 截止日期 "YYYYMMDD"。
            adjust: 复权类型 "qfq"前复权 / "hfq"后复权 / ""不复权。

        Returns:
            统一 Schema DataFrame，index 为 date。
        """
        ...

    @abstractmethod
    def get_realtime_quote(self, symbols: list[str]) -> pd.DataFrame:
        """获取实时行情快照。

        Args:
            symbols: 股票代码列表。

        Returns:
            包含最新价、涨跌幅等字段的 DataFrame。
        """
        ...

    @abstractmethod
    def supported_markets(self) -> list[str]:
        """返回支持的市场列表。"""
        ...

    def get_name(self) -> str:
        """返回数据源名称。"""
        return self.__class__.__name__
