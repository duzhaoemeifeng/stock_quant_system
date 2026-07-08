"""BaoStock A股数据源实现。

BaoStock (baostock.com) 免费证券数据，无需注册或 API Key。
证监会有 CSA 认证，数据来源于交易所官方。
"""

import time
from datetime import datetime

import baostock as bs
import pandas as pd

from .base import DataSource, apply_schema, Col

# baostock -> 统一 Schema 列名映射
BAOSTOCK_COLUMN_MAP: dict[str, str] = {
    "date": Col.DATE,
    "open": Col.OPEN,
    "high": Col.HIGH,
    "low": Col.LOW,
    "close": Col.CLOSE,
    "volume": Col.VOLUME,
    "amount": Col.AMOUNT,
    "pctChg": Col.PCT_CHG,
    "turn": Col.TURNOVER,
}

_SH_PREFIXES = ("6", "9")
_SZ_PREFIXES = ("0", "2", "3")


def _to_baostock_code(symbol: str) -> str:
    """将 6 位股票代码转为 baostock 格式 (sh.600000 / sz.000001)."""
    s = symbol.strip()
    if s.startswith(_SH_PREFIXES):
        return f"sh.{s}"
    return f"sz.{s}"


class BaoStockSource(DataSource):
    """BaoStock 数据源。

    使用 baostock 免注册接口下载 A 股历史日线数据。
    每次使用前自动 login，使用后自动 logout。
    """

    def __init__(self, request_delay: float = 0.5):
        self._request_delay = request_delay
        self._logged_in = False

    def _ensure_login(self):
        if not self._logged_in:
            lg = bs.login()
            if lg.error_code != "0":
                raise RuntimeError(f"BaoStock 登录失败: {lg.error_msg}")
            self._logged_in = True

    def _logout(self):
        if self._logged_in:
            bs.logout()
            self._logged_in = False

    def download_daily_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """下载A股日线数据。"""
        self._ensure_login()

        bs_code = _to_baostock_code(symbol)
        adjust_map = {"qfq": "2", "hfq": "1", "": "3"}
        bs_adjust = adjust_map.get(adjust, "2")

        fields = "date,open,high,low,close,volume,amount,turn,pctChg"
        # baostock 需要 YYYY-MM-DD 格式
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        try:
            rs = bs.query_history_k_data_plus(
                bs_code, fields,
                start_date=start, end_date=end,
                frequency="d", adjustflag=bs_adjust,
            )
            if rs is None or rs.error_code != "0":
                raise RuntimeError(f"BaoStock 查询失败: {rs.error_msg}")

            rows = []
            while rs.next():
                rows.append(rs.get_row_data())

            time.sleep(self._request_delay)
        except Exception:
            self._logout()
            raise

        if not rows:
            return pd.DataFrame()

        columns = fields.split(",")
        df = pd.DataFrame(rows, columns=columns)
        df.rename(columns=BAOSTOCK_COLUMN_MAP, inplace=True)
        df[Col.SYMBOL] = symbol
        df[Col.DATE] = pd.to_datetime(df[Col.DATE], errors="coerce")
        df.set_index(Col.DATE, inplace=True)

        numeric_cols = [Col.OPEN, Col.HIGH, Col.LOW, Col.CLOSE,
                        Col.VOLUME, Col.AMOUNT, Col.PCT_CHG, Col.TURNOVER]
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        keep = [c for c in [Col.SYMBOL, Col.OPEN, Col.HIGH, Col.LOW,
                             Col.CLOSE, Col.VOLUME, Col.AMOUNT,
                             Col.PCT_CHG, Col.TURNOVER] if c in df.columns]
        return df[keep].sort_index()

    def download_multiple(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> dict[str, pd.DataFrame]:
        """批量下载多只股票数据。"""
        results = {}
        for sym in symbols:
            try:
                results[sym] = self.download_daily_bars(
                    sym, start_date, end_date, adjust
                )
            except RuntimeError:
                results[sym] = pd.DataFrame()
        self._logout()
        return results

    def get_realtime_quote(self, symbols: list[str]) -> pd.DataFrame:
        """BaoStock 不提供实时行情，返回空 DataFrame。"""
        return pd.DataFrame()

    def supported_markets(self) -> list[str]:
        return ["A股"]

    def download_index_daily(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """下载指数日线数据（如上证指数 sh.000001）。"""
        self._ensure_login()
        fields = "date,open,high,low,close,volume,amount"
        start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
        try:
            rs = bs.query_history_k_data_plus(
                index_code, fields,
                start_date=start, end_date=end,
                frequency="d", adjustflag="3",
            )
            if rs is None or rs.error_code != "0":
                raise RuntimeError(f"BaoStock 查询失败: {rs.error_msg}")

            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            time.sleep(self._request_delay)
        except Exception:
            self._logout()
            raise

        if not rows:
            return pd.DataFrame()

        columns = fields.split(",")
        df = pd.DataFrame(rows, columns=columns)
        df.rename(columns=BAOSTOCK_COLUMN_MAP, inplace=True)
        df[Col.SYMBOL] = index_code
        df[Col.DATE] = pd.to_datetime(df[Col.DATE], errors="coerce")
        df.set_index(Col.DATE, inplace=True)
        for c in [Col.OPEN, Col.HIGH, Col.LOW, Col.CLOSE, Col.VOLUME, Col.AMOUNT]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df.sort_index()
