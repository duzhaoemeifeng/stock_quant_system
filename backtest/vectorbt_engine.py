"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。本回测引擎为简化实现，
 用于教学目的。复杂策略建议使用 backtrader。
==================================================
基于 numpy/pandas 的轻量回测引擎。

使用向量化方式逐日模拟交易，支持：
- 信号驱动开仓/平仓
- 仓位管理
- 风控拦截
- 滑点与手续费
- A股 T+1 规则（当日买入次日可卖）
"""

import numpy as np
import pandas as pd

from .base import BacktestEngine
from .result import BacktestResult
from .slippage import SlippageModel
from .metrics import MetricsCalculator
from ..data.base import Col
from ..portfolio.base import PositionSizer, RiskContext
from ..portfolio.risk_manager import RiskManager


class SimpleBacktestEngine(BacktestEngine):
    """简化向量化回测引擎。

    不依赖 vectorbt 或 backtrader，适合快速验证策略逻辑。
    遵守 A股 T+1 规则：今日买入后明日方可卖出。

    使用方法:
        engine = SimpleBacktestEngine()
        result = engine.run(data, signals, sizer, risk_manager, slippage)
    """

    def run(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame,
        position_sizer: PositionSizer | None = None,
        risk_manager: RiskManager | None = None,
        slippage_model: SlippageModel | None = None,
        initial_capital: float = 1_000_000.0,
    ) -> BacktestResult:
        slippage = slippage_model or SlippageModel()

        n = len(data)
        equity = np.zeros(n)
        cash = np.zeros(n)
        position = np.zeros(n)       # 持仓股数
        avg_cost = np.zeros(n)       # 持仓成本

        equity[0] = initial_capital
        cash[0] = initial_capital

        trades = []
        peak_capital = initial_capital
        consecutive_losses = 0
        last_trade_pnl = 0.0
        daily_capital_start = initial_capital
        last_date = None

        prices = data[Col.CLOSE].values
        highs = data[Col.HIGH].values if Col.HIGH in data.columns else prices
        lows = data[Col.LOW].values if Col.LOW in data.columns else prices
        dates = data.index

        signal_series = signals.get("signal", pd.Series(np.nan, index=data.index))
        strength_series = signals.get(
            "signal_strength", pd.Series(1.0, index=data.index)
        )

        for i in range(1, n):
            # 每日开始时更新
            current_date = dates[i]
            if last_date is None or current_date.date() != last_date:
                daily_capital_start = equity[i - 1]
            last_date = current_date.date()

            price = prices[i]
            sig = signal_series.iloc[i]
            strength = strength_series.iloc[i] if pd.notna(strength_series.iloc[i]) else 1.0

            # 默认继承上日
            cash[i] = cash[i - 1]
            position[i] = position[i - 1]
            avg_cost[i] = avg_cost[i - 1]

            # ---- 风控检查 ----
            if risk_manager is not None and position[i] != 0:
                context = RiskContext(
                    current_capital=cash[i] + position[i] * price,
                    peak_capital=peak_capital,
                    positions={
                        "default": {
                            "quantity": position[i],
                            "entry_price": avg_cost[i] if avg_cost[i] > 0 else price,
                            "peak_price": max(avg_cost[i], highs[i]),
                        }
                    },
                    daily_pnl=(cash[i] + position[i] * price) - daily_capital_start,
                    daily_start_capital=daily_capital_start,
                    consecutive_losses=consecutive_losses,
                    current_prices={"default": price},
                )
                decision = risk_manager.check_all(context)
                if not decision.approved and decision.action in ("close_all", "halt_trading"):
                    if position[i] != 0:
                        actual_price, fee = slippage.apply_sell(price, int(abs(position[i])))
                        cash[i] += actual_price * abs(position[i]) - fee
                        pnl = (actual_price - avg_cost[i]) * abs(position[i]) - fee
                        trades.append({
                            "entry_date": None,
                            "exit_date": dates[i],
                            "entry_price": avg_cost[i],
                            "exit_price": actual_price,
                            "quantity": abs(position[i]),
                            "pnl": pnl,
                            "commission": fee,
                            "exit_reason": decision.reason or "风控平仓",
                        })
                        last_trade_pnl = pnl
                        if pnl < 0:
                            consecutive_losses += 1
                        else:
                            consecutive_losses = 0
                        position[i] = 0
                        avg_cost[i] = 0
                    if decision.action == "halt_trading":
                        equity[i] = cash[i] + position[i] * price
                        peak_capital = max(peak_capital, equity[i])
                        continue

            # ---- 信号处理 ----
            if pd.notna(sig) and sig != 0:
                if position_sizer is not None:
                    target_shares = position_sizer.calculate(
                        capital=cash[i],
                        price=price,
                        signal_strength=strength,
                        data=data.iloc[: i + 1],
                    )
                else:
                    target_shares = int(cash[i] * 0.1 / price)

                if sig > 0 and position[i] == 0:
                    # 买入信号
                    buy_shares = min(target_shares, int(cash[i] / price))
                    if buy_shares >= 100:
                        buy_shares = (buy_shares // 100) * 100  # A股整手
                        actual_price, fee = slippage.apply_buy(price, buy_shares)
                        cost = actual_price * buy_shares + fee
                        if cost <= cash[i]:
                            cash[i] -= cost
                            position[i] = buy_shares
                            avg_cost[i] = actual_price
                            # 记录开仓
                            trades.append({
                                "entry_date": dates[i],
                                "exit_date": None,
                                "entry_price": actual_price,
                                "exit_price": None,
                                "quantity": buy_shares,
                                "pnl": 0.0,
                                "commission": fee,
                                "exit_reason": None,
                            })

                elif sig < 0 and position[i] > 0:
                    # 卖出信号：平仓
                    actual_price, fee = slippage.apply_sell(price, int(position[i]))
                    cash[i] += actual_price * position[i] - fee
                    pnl = (actual_price - avg_cost[i]) * position[i] - fee

                    # 更新最后一笔开仓交易的平仓信息
                    for t in reversed(trades):
                        if t["exit_date"] is None:
                            t["exit_date"] = dates[i]
                            t["exit_price"] = actual_price
                            t["pnl"] = pnl
                            t["commission"] += fee
                            t["exit_reason"] = "信号平仓"
                            break

                    last_trade_pnl = pnl
                    if pnl < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0

                    position[i] = 0
                    avg_cost[i] = 0

            # 更新权益
            equity[i] = cash[i] + position[i] * price
            peak_capital = max(peak_capital, equity[i])

        # ---- 构建结果 ----
        equity_s = pd.Series(equity, index=data.index)
        daily_rets = pd.Series(np.diff(equity) / equity[:-1], index=data.index[1:])

        trade_df = pd.DataFrame(trades)
        # 分离已完成和未完成的交易
        if not trade_df.empty:
            completed = trade_df[trade_df["exit_date"].notna()].copy()
            # 未平仓按最后价格估值
            open_trades = trade_df[trade_df["exit_date"].isna()]
            if not open_trades.empty:
                last_price = prices[-1]
                for idx in open_trades.index:
                    open_trades.loc[idx, "exit_price"] = last_price
                    open_trades.loc[idx, "exit_date"] = dates[-1]
                    q = open_trades.loc[idx, "quantity"]
                    ep = open_trades.loc[idx, "entry_price"]
                    open_trades.loc[idx, "pnl"] = (last_price - ep) * q
                completed = pd.concat([completed, open_trades])
            trade_df = completed

        stats = MetricsCalculator.trade_statistics(trade_df)
        total_ret = (equity[-1] / initial_capital) - 1.0
        ann_ret = MetricsCalculator.annual_return(total_ret, n)
        max_dd, max_dd_days = MetricsCalculator.max_drawdown(equity_s)

        result = BacktestResult(
            equity_curve=equity_s,
            total_return=total_ret,
            annual_return=ann_ret,
            annual_volatility=MetricsCalculator.annual_volatility(daily_rets),
            sharpe_ratio=MetricsCalculator.sharpe_ratio(daily_rets),
            calmar_ratio=MetricsCalculator.calmar_ratio(ann_ret, max_dd),
            max_drawdown=max_dd,
            max_drawdown_days=max_dd_days,
            trade_count=stats["trade_count"],
            win_count=stats["win_count"],
            loss_count=stats["loss_count"],
            win_rate=stats["win_rate"],
            avg_win=stats["avg_win"],
            avg_loss=stats["avg_loss"],
            win_loss_ratio=stats["win_loss_ratio"],
            profit_factor=stats["profit_factor"],
            daily_returns=daily_rets,
            trade_list=trade_df,
            total_commission=stats["total_commission"],
        )
        return result
