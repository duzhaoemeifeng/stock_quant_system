"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
回撤曲线（水下曲线）。
"""

import matplotlib.pyplot as plt
import pandas as pd

from ..backtest.result import BacktestResult


def plot_drawdown(
    result: BacktestResult,
    title: str = "回撤曲线",
    figsize: tuple = (12, 4),
) -> plt.Figure:
    """绘制回撤曲线。

    Args:
        result: 回测结果。
        title: 图表标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig, ax = plt.subplots(figsize=figsize)

    equity = result.equity_curve
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100  # 百分比

    ax.fill_between(
        equity.index, 0, drawdown,
        color="#F44336", alpha=0.3, label="回撤",
    )
    ax.plot(
        equity.index, drawdown,
        color="#D32F2F", linewidth=0.8,
    )

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("日期")
    ax.set_ylabel("回撤 (%)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))
    ax.grid(True, alpha=0.3)

    # 标注最大回撤
    max_dd_idx = drawdown.idxmin()
    max_dd_val = drawdown.min()
    if pd.notna(max_dd_idx):
        ax.annotate(
            f"最大回撤: {max_dd_val:.1f}%",
            xy=(max_dd_idx, max_dd_val),
            xytext=(10, -20),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="darkred"),
            fontsize=9, color="darkred",
        )

    fig.tight_layout()
    return fig
