"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。数据来源于 AKShare 免费接口，
 可能存在延迟或缺失。
==================================================
AKShare A股数据源实现。
"""

import time
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

from .base import DataSource, apply_schema


class AKShareSource(DataSource):
    """AKShare A股数据源。

    使用 akshare.stock_zh_a_hist 获取A股历史日线数据。
    免费、无需 API Key，但请求频率不宜过高。

    使用方法:
        source = AKShareSource()
        df = source.download_daily_bars("000001", "20240101", "20240630")
    """

    def __init__(self, request_delay: float = 1.0):
        self._request_delay = request_delay

    def download_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """下载A股日线数据。

        Args:
            symbol: 6位股票代码，如 "000001"。
            start_date: 起始日期 "YYYYMMDD"。
            end_date: 截止日期 "YYYYMMDD"。
            adjust: "qfq"前复权 / "hfq"后复权 / ""不复权。
        """
        period = self._map_adjust(adjust)

        try:
            raw = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
            time.sleep(self._request_delay)
        except Exception as e:
            raise RuntimeError(
                f"AKShare 下载 {symbol} 数据失败: {e}"
            ) from e

        if raw is None or raw.empty:
            return pd.DataFrame()

        df = apply_schema(raw, source="akshare", symbol=symbol)
        return df

    def download_multiple(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> dict[str, pd.DataFrame]:
        """批量下载多只股票数据。

        Returns:
            {symbol: DataFrame} 字典。
        """
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.download_daily_bars(
                    sym, start_date, end_date, adjust
                )
            except RuntimeError:
                results[sym] = pd.DataFrame()
        return results

    def get_realtime_quote(self, symbols: list[str]) -> pd.DataFrame:
        """获取A股实时行情快照。"""
        try:
            df = ak.stock_zh_a_spot_em()
            time.sleep(self._request_delay)
        except Exception as e:
            raise RuntimeError(f"获取实时行情失败: {e}") from e

        if df is None or df.empty:
            return pd.DataFrame()

        df = df[df["代码"].isin(symbols)].copy()
        from .base import AKSHARE_COLUMN_MAP
        rename_map = {k: v for k, v in AKSHARE_COLUMN_MAP.items() if k in df.columns}
        df.rename(columns=rename_map, inplace=True)
        return df

    def supported_markets(self) -> list[str]:
        return ["A股"]

    @staticmethod
    def _map_adjust(adjust: str) -> str:
        """映射复权类型到 AKShare 参数。"""
        mapping = {"qfq": "qfq", "hfq": "hfq", "": ""}
        return mapping.get(adjust, "qfq")
