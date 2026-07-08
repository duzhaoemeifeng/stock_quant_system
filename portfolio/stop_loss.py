"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。止损规则无法应对跳空缺口和
 一字跌停等极端情况。
==================================================
固定比例止损规则。
"""

from .base import RiskContext, RiskDecision, RiskRule


class FixedStopLoss(RiskRule):
    """固定比例止损。

    params:
        stop_loss_pct: 止损比例（默认 0.07 = 7%）。
        当持仓亏损超过此比例时，强制平仓。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.stop_loss_pct = self.params.get("stop_loss_pct", 0.07)

    def check(self, context: RiskContext) -> RiskDecision:
        for symbol, pos in context.positions.items():
            if pos.get("quantity", 0) == 0:
                continue
            entry_price = pos.get("entry_price", 0)
            current_price = context.current_prices.get(symbol, 0)
            if entry_price <= 0 or current_price <= 0:
                continue

            pnl_pct = (current_price - entry_price) / entry_price
            if pnl_pct < -self.stop_loss_pct:
                return RiskDecision(
                    approved=False,
                    reason=f"{symbol} 亏损 {pnl_pct:.2%}，触发 {self.stop_loss_pct:.0%} 止损",
                    action="close_all",
                )

        return RiskDecision(approved=True)
