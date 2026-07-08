"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
盈亏分布直方图。
"""

import matplotlib.pyplot as plt
import numpy as np

from ..backtest.result import BacktestResult


def plot_pnl_histogram(
    result: BacktestResult,
    bins: int = 30,
    title: str = "盈亏分布",
    figsize: tuple = (10, 6),
) -> plt.Figure:
    """绘制逐笔盈亏分布直方图。

    Args:
        result: 回测结果，含 trade_list。
        bins: 直方图桶数。
        title: 图表标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig, ax = plt.subplots(figsize=figsize)

    trades = result.trade_list
    if trades is None or trades.empty:
        ax.text(0.5, 0.5, "无交易数据", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        return fig

    pnl = trades["pnl"].dropna()
    if len(pnl) == 0:
        return fig

    colors = ["#F44336" if x < 0 else "#4CAF50" for x in pnl]
    ax.hist(pnl, bins=bins, color="#2196F3", alpha=0.7, edgecolor="white")

    # 统计线
    mean_pnl = pnl.mean()
    ax.axvline(x=mean_pnl, color="#FF9800", linestyle="--", linewidth=2,
               label=f"均值: {mean_pnl:,.0f}")
    ax.axvline(x=0, color="gray", linestyle=":", linewidth=1)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("每笔盈亏 (元)")
    ax.set_ylabel("频次")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")

    # 右上角统计信息
    win_rate = (pnl > 0).mean()
    textstr = f"胜率: {win_rate:.1%}\n均值: {mean_pnl:,.0f}\n标准差: {pnl.std():,.0f}"
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    fig.tight_layout()
    return fig
