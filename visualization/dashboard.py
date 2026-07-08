"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
综合看板：四合一组合图。
"""

import matplotlib.pyplot as plt
import pandas as pd

from ..backtest.result import BacktestResult

from .equity_curve import plot_equity_curve
from .drawdown import plot_drawdown
from .trades import plot_trades
from .pnl_histogram import plot_pnl_histogram


def plot_dashboard(
    result: BacktestResult,
    data: pd.DataFrame | None = None,
    benchmark: pd.Series | None = None,
    title: str = "策略回测综合看板",
    figsize: tuple = (16, 12),
) -> plt.Figure:
    """绘制四合一综合看板。

    布局:
        左上：权益曲线 vs 基准
        右上：回撤曲线
        左下：买卖点标记
        右下：盈亏分布直方图

    Args:
        result: 回测结果。
        data: 原始 OHLCV 数据（买卖点标记需要）。
        benchmark: 基准走势。
        title: 总标题。
        figsize: 图表尺寸。

    Returns:
        matplotlib Figure。
    """
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, fontsize=15, fontweight="bold", y=0.98)

    # 左上：权益曲线
    ax1 = fig.add_subplot(2, 2, 1)
    _plot_equity_on_ax(ax1, result, benchmark)

    # 右上：回撤曲线
    ax2 = fig.add_subplot(2, 2, 2)
    _plot_drawdown_on_ax(ax2, result)

    # 左下：买卖点标记
    ax3 = fig.add_subplot(2, 2, 3)
    if data is not None:
        _plot_trades_on_ax(ax3, data, result)
    else:
        ax3.text(0.5, 0.5, "无OHLCV数据", ha="center", va="center",
                 transform=ax3.transAxes, fontsize=12, color="gray")

    # 右下：盈亏直方图
    ax4 = fig.add_subplot(2, 2, 4)
    _plot_pnl_on_ax(ax4, result)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def _plot_equity_on_ax(ax, result, benchmark):
    equity = result.equity_curve
    initial = equity.iloc[0]
    ax.plot(equity.index, equity / initial, color="#2196F3", linewidth=1.2, label="策略")
    if benchmark is not None and len(benchmark) > 0:
        bench_norm = benchmark / benchmark.iloc[0]
        ax.plot(bench_norm.index, bench_norm, color="#FF9800",
                linewidth=1.0, linestyle="--", label="基准")
    ax.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    ax.set_title("权益曲线", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)


def _plot_drawdown_on_ax(ax, result):
    equity = result.equity_curve
    peak = equity.expanding().max()
    drawdown = (equity - peak) / peak * 100
    ax.fill_between(equity.index, 0, drawdown, color="#F44336", alpha=0.3)
    ax.plot(equity.index, drawdown, color="#D32F2F", linewidth=0.8)
    ax.set_title("回撤曲线", fontsize=11, fontweight="bold")
    ax.set_ylabel("回撤 (%)")
    ax.grid(True, alpha=0.3)


def _plot_trades_on_ax(ax, data, result):
    close = data.get("close", data.iloc[:, 3])
    ax.plot(data.index, close, color="#333", linewidth=0.8, alpha=0.7)
    trades = result.trade_list
    if trades is not None and not trades.empty:
        entries = trades[trades["entry_date"].notna()]
        if len(entries) > 0:
            ax.scatter(entries["entry_date"], entries["entry_price"],
                       marker="^", s=60, color="#4CAF50", label="买入", zorder=5)
        exits = trades[trades["exit_date"].notna()]
        if len(exits) > 0:
            ax.scatter(exits["exit_date"], exits["exit_price"],
                       marker="v", s=60, color="#F44336", label="卖出", zorder=5)
    ax.set_title("交易信号", fontsize=11, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)


def _plot_pnl_on_ax(ax, result):
    trades = result.trade_list
    if trades is not None and not trades.empty:
        pnl = trades["pnl"].dropna()
        if len(pnl) > 0:
            ax.hist(pnl, bins=25, color="#2196F3", alpha=0.7, edgecolor="white")
            ax.axvline(x=pnl.mean(), color="#FF9800", linestyle="--", linewidth=1.5)
            ax.axvline(x=0, color="gray", linestyle=":", linewidth=1)
    ax.set_title("盈亏分布", fontsize=11, fontweight="bold")
    ax.set_xlabel("每笔盈亏 (元)")
    ax.grid(True, alpha=0.3, axis="y")
