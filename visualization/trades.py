"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
买卖点标记图：在价格K线上标注交易进出场点。
"""

import matplotlib.pyplot as plt
import pandas as pd

from ..backtest.result import BacktestResult


def plot_trades(
    data: pd.DataFrame,
    result: BacktestResult,
    title: str = "交易信号标记",
    figsize: tuple = (14, 7),
) -> plt.Figure:
    """在价格走势图上标注买卖点。

    Args:
        data: 原始 OHLCV 数据。
        result: 回测结果，含 trade_list。
        title: 图表标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig, ax = plt.subplots(figsize=figsize)

    close = data.get("close", data.iloc[:, 3]) if hasattr(data, "get") else data
    ax.plot(data.index, close, color="#333333", linewidth=1.0, label="收盘价", alpha=0.7)

    trades = result.trade_list
    if trades is not None and not trades.empty:
        entry_dates = trades["entry_date"].dropna()
        entry_prices = trades.loc[entry_dates.index, "entry_price"]
        if len(entry_dates) > 0:
            ax.scatter(entry_dates, entry_prices, marker="^", s=80,
                       color="#4CAF50", zorder=5, label="买入", edgecolors="white")

        exit_mask = trades["exit_date"].notna() & (trades["quantity"] > 0)
        exit_dates = trades.loc[exit_mask, "exit_date"]
        exit_prices = trades.loc[exit_mask, "exit_price"]
        if len(exit_dates) > 0:
            ax.scatter(exit_dates, exit_prices, marker="v", s=80,
                       color="#F44336", zorder=5, label="卖出", edgecolors="white")

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("日期")
    ax.set_ylabel("价格")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig
