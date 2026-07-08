"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
日内亏损限制与总回撤限制规则。
"""

from .base import RiskContext, RiskDecision, RiskRule


class DailyLossLimit(RiskRule):
    """单日最大亏损限制。

    params:
        max_daily_loss_pct: 当日最大亏损比例（默认 0.03 = 3%）。
        当日亏损超过初始资金 * 此比例时，暂停当日剩余交易。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.max_daily_loss_pct = self.params.get("max_daily_loss_pct", 0.03)

    def check(self, context: RiskContext) -> RiskDecision:
        if context.daily_start_capital <= 0:
            return RiskDecision(approved=True)

        max_loss = context.daily_start_capital * self.max_daily_loss_pct
        if context.daily_pnl < -max_loss:
            return RiskDecision(
                approved=False,
                reason=(
                    f"当日亏损 {context.daily_pnl:.0f}，"
                    f"超过限额 {max_loss:.0f} ({self.max_daily_loss_pct:.0%})"
                ),
                action="halt_trading",
            )

        return RiskDecision(approved=True)


class MaxDrawdownLimit(RiskRule):
    """总回撤阈值限制。

    params:
        max_drawdown_pct: 最大回撤比例（默认 0.25 = 25%）。
        账户从峰值回撤超过此比例时，全部平仓并暂停交易。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.max_drawdown_pct = self.params.get("max_drawdown_pct", 0.25)

    def check(self, context: RiskContext) -> RiskDecision:
        if context.peak_capital <= 0:
            return RiskDecision(approved=True)

        drawdown = (context.current_capital - context.peak_capital) / context.peak_capital
        if drawdown < -self.max_drawdown_pct:
            return RiskDecision(
                approved=False,
                reason=(
                    f"总回撤 {drawdown:.2%}，"
                    f"超过阈值 {self.max_drawdown_pct:.0%}"
                ),
                action="halt_trading",
            )

        return RiskDecision(approved=True)


class ConsecutiveLossLimit(RiskRule):
    """连续亏损暂停交易规则。

    params:
        max_consecutive: 最大连续亏损次数（默认 5）。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.max_consecutive = self.params.get("max_consecutive", 5)

    def check(self, context: RiskContext) -> RiskDecision:
        if context.consecutive_losses >= self.max_consecutive:
            return RiskDecision(
                approved=False,
                reason=f"连续亏损 {context.consecutive_losses} 次，暂停交易",
                action="halt_trading",
            )
        return RiskDecision(approved=True)
