"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。绩效指标均为统计学度量，
 不应作为投资决策的唯一依据。
==================================================
绩效指标计算器：夏普、卡玛、最大回撤、胜率、盈亏比等。
"""

import numpy as np
import pandas as pd


class MetricsCalculator:
    """绩效指标静态计算器。

    TRADING_DAYS_PER_YEAR = 252
    """

    TRADING_DAYS = 252

    @classmethod
    def sharpe_ratio(
        cls,
        daily_returns: pd.Series,
        risk_free_rate: float = 0.03,
    ) -> float:
        """计算年化夏普比率。

        Sharpe = (年化收益 - 无风险利率) / 年化波动率
        """
        ann_return = daily_returns.mean() * cls.TRADING_DAYS
        ann_vol = daily_returns.std() * np.sqrt(cls.TRADING_DAYS)
        if ann_vol == 0:
            return 0.0
        return (ann_return - risk_free_rate) / ann_vol

    @classmethod
    def max_drawdown(cls, equity_curve: pd.Series) -> tuple[float, int]:
        """计算最大回撤及其持续天数。

        Returns:
            (max_drawdown_pct, max_drawdown_duration_days)
        """
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak
        max_dd = drawdown.min()

        # 计算最长回撤持续天数
        duration = 0
        max_duration = 0
        for dd in drawdown:
            if dd < 0:
                duration += 1
                max_duration = max(max_duration, duration)
            else:
                duration = 0

        return float(max_dd), max_duration

    @classmethod
    def calmar_ratio(
        cls, annual_return: float, max_drawdown: float
    ) -> float:
        """卡玛比率 = 年化收益率 / |最大回撤|。"""
        if max_drawdown == 0:
            return 0.0
        return annual_return / abs(max_drawdown)

    @classmethod
    def total_return(cls, equity_curve: pd.Series) -> float:
        """累计收益率。"""
        return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0

    @classmethod
    def annual_return(
        cls, total_return: float, n_days: int
    ) -> float:
        """年化收益率。"""
        if n_days <= 0:
            return 0.0
        return (1.0 + total_return) ** (cls.TRADING_DAYS / n_days) - 1.0

    @classmethod
    def annual_volatility(cls, daily_returns: pd.Series) -> float:
        """年化波动率。"""
        return daily_returns.std() * np.sqrt(cls.TRADING_DAYS)

    @classmethod
    def trade_statistics(
        cls, trade_list: pd.DataFrame
    ) -> dict:
        """从逐笔交易记录计算统计指标。

        Args:
            trade_list: 每行一笔交易，包含 'pnl' 列。

        Returns:
            dict with: trade_count, win_count, loss_count, win_rate,
                      avg_win, avg_loss, win_loss_ratio, profit_factor,
                      total_pnl, total_commission
        """
        if trade_list.empty:
            return {
                "trade_count": 0, "win_count": 0, "loss_count": 0,
                "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "win_loss_ratio": 0.0, "profit_factor": 0.0,
                "total_pnl": 0.0, "total_commission": 0.0,
            }

        pnl = trade_list.get("pnl", pd.Series(0, index=trade_list.index))
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        total_wins = wins.sum() if len(wins) > 0 else 0.0
        total_losses = abs(losses.sum()) if len(losses) > 0 else 0.0

        return {
            "trade_count": len(trade_list),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": len(wins) / len(trade_list) if len(trade_list) > 0 else 0.0,
            "avg_win": wins.mean() if len(wins) > 0 else 0.0,
            "avg_loss": losses.mean() if len(losses) > 0 else 0.0,
            "win_loss_ratio": (abs(wins.mean() / losses.mean())
                               if len(wins) > 0 and len(losses) > 0 and losses.mean() != 0
                               else 0.0),
            "profit_factor": (total_wins / total_losses
                              if total_losses > 0 else float("inf")),
            "total_pnl": pnl.sum(),
            "total_commission": trade_list.get("commission", pd.Series(0)).sum(),
        }

    @classmethod
    def compute_all(
        cls,
        equity_curve: pd.Series,
        trade_list: pd.DataFrame | None = None,
        risk_free_rate: float = 0.03,
    ) -> dict:
        """一次性计算所有指标。

        Returns:
            包含所有指标的 dict。
        """
        daily_returns = equity_curve.pct_change().dropna()
        total_ret = cls.total_return(equity_curve)
        ann_ret = cls.annual_return(total_ret, len(equity_curve))
        max_dd, max_dd_days = cls.max_drawdown(equity_curve)

        metrics = {
            "total_return": total_ret,
            "annual_return": ann_ret,
            "annual_volatility": cls.annual_volatility(daily_returns),
            "sharpe_ratio": cls.sharpe_ratio(daily_returns, risk_free_rate),
            "calmar_ratio": cls.calmar_ratio(ann_ret, max_dd),
            "max_drawdown": max_dd,
            "max_drawdown_days": max_dd_days,
        }

        if trade_list is not None and not trade_list.empty:
            metrics.update(cls.trade_statistics(trade_list))

        return metrics
