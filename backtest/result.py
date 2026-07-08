"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
标准化回测结果数据类。
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    """标准化回测输出。

    所有回测引擎统一返回此格式，可视化与优化模块
    只需依赖此数据类，不感知底层引擎差异。

    风险提示：回测结果仅为历史模拟，不代表未来收益。
    """

    # 权益曲线
    equity_curve: pd.Series = field(default_factory=pd.Series)
    benchmark_curve: pd.Series | None = None

    # 核心绩效指标
    total_return: float = 0.0
    annual_return: float = 0.0
    annual_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_days: int = 0

    # 交易统计
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    win_loss_ratio: float = 0.0
    profit_factor: float = 0.0

    # 分布数据
    daily_returns: pd.Series = field(default_factory=pd.Series)
    trade_list: pd.DataFrame = field(default_factory=pd.DataFrame)

    # 成本
    total_commission: float = 0.0
    total_slippage: float = 0.0

    def summary(self) -> str:
        """生成文本摘要。"""
        lines = [
            "=" * 50,
            "  回测结果摘要",
            "=" * 50,
            f"  累计收益率:     {self.total_return:>8.2%}",
            f"  年化收益率:     {self.annual_return:>8.2%}",
            f"  年化波动率:     {self.annual_volatility:>8.2%}",
            f"  夏普比率:       {self.sharpe_ratio:>8.2f}",
            f"  卡玛比率:       {self.calmar_ratio:>8.2f}",
            f"  最大回撤:       {self.max_drawdown:>8.2%}",
            f"  回撤持续(天):   {self.max_drawdown_days:>8}",
            "-" * 50,
            f"  交易次数:       {self.trade_count:>8}",
            f"  胜率:           {self.win_rate:>8.2%}",
            f"  平均盈利:       {self.avg_win:>8.2f}",
            f"  平均亏损:       {self.avg_loss:>8.2f}",
            f"  盈亏比:         {self.win_loss_ratio:>8.2f}",
            f"  盈利因子:       {self.profit_factor:>8.2f}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """转为字典，便于序列化。"""
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "annual_volatility": self.annual_volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_days": self.max_drawdown_days,
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.win_rate,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "win_loss_ratio": self.win_loss_ratio,
            "profit_factor": self.profit_factor,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
        }
