"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
信号散点图：信号强度 vs 未来收益。
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def plot_signal_scatter(
    signal_strength: pd.Series,
    forward_returns: pd.Series,
    title: str = "信号强度 vs 未来收益",
    figsize: tuple = (8, 6),
) -> plt.Figure:
    """绘制信号强度与未来收益的散点图。

    用于评估信号的预测能力（IC分析可视化）。

    Args:
        signal_strength: 信号强度序列。
        forward_returns: 对应的未来收益序列。
        title: 图表标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig, ax = plt.subplots(figsize=figsize)

    # 对齐
    common_idx = signal_strength.index.intersection(forward_returns.index)
    x = signal_strength[common_idx].dropna()
    y = forward_returns[common_idx].dropna()
    common = x.index.intersection(y.index)
    x = x[common]
    y = y[common]

    if len(x) < 5:
        ax.text(0.5, 0.5, "数据不足", ha="center", va="center",
                transform=ax.transAxes, fontsize=14, color="gray")
        return fig

    ax.scatter(x, y, alpha=0.4, s=15, color="#2196F3", edgecolors="none")

    # 回归线
    slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
    x_line = np.linspace(x.min(), x.max(), 100)
    ax.plot(x_line, slope * x_line + intercept, color="#FF5722",
            linewidth=2, label=f"R={r_value:.3f} (p={p_value:.3f})")

    # IC 信息
    ic = x.corr(y)
    ax.text(0.05, 0.95, f"IC: {ic:.4f}", transform=ax.transAxes,
            fontsize=11, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    ax.axhline(y=0, color="gray", linestyle=":", alpha=0.5)
    ax.axvline(x=0, color="gray", linestyle=":", alpha=0.5)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("信号强度")
    ax.set_ylabel("未来收益率")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig
