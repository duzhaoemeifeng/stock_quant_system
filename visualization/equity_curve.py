"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
权益曲线 vs 基准走势对比图。
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from ..backtest.result import BacktestResult


def plot_equity_curve(
    result: BacktestResult,
    benchmark: pd.Series | None = None,
    title: str = "权益曲线",
    figsize: tuple = (12, 6),
) -> plt.Figure:
    """绘制权益曲线与基准对比。

    Args:
        result: 回测结果。
        benchmark: 基准走势 Series（如指数）。
        title: 图表标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig, ax = plt.subplots(figsize=figsize)

    equity = result.equity_curve
    initial = equity.iloc[0]
    normalized = equity / initial

    ax.plot(
        equity.index, normalized, label="策略权益",
        color="#2196F3", linewidth=1.5,
    )

    if benchmark is not None and len(benchmark) > 0:
        bench_norm = benchmark / benchmark.iloc[0]
        # 对齐索引
        common_idx = normalized.index.intersection(bench_norm.index)
        if len(common_idx) > 0:
            ax.plot(
                common_idx, bench_norm[common_idx],
                label="基准", color="#FF9800",
                linewidth=1.2, linestyle="--",
            )

    ax.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("日期")
    ax.set_ylabel("净值")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    # 标注最大回撤区域
    peak = equity.expanding().max()
    dd = (equity - peak) / peak
    dd_start = dd.idxmin()
    if pd.notna(dd_start):
        ax.axvline(x=dd_start, color="red", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return fig
