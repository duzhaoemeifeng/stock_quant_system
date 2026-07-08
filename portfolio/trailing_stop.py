"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
移动止损（Trailing Stop）规则。
"""

from .base import RiskContext, RiskDecision, RiskRule


class TrailingStop(RiskRule):
    """移动止损规则。

    params:
        trailing_pct: 回撤比例（默认 0.15 = 15%）。
        从持仓期间最高价回撤超过此比例时，强制平仓。

    逻辑：peak 是持仓期间的最高价，当现价 < peak * (1 - trailing_pct) 时触发。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.trailing_pct = self.params.get("trailing_pct", 0.15)

    def check(self, context: RiskContext) -> RiskDecision:
        for symbol, pos in context.positions.items():
            if pos.get("quantity", 0) == 0:
                continue
            peak_price = pos.get("peak_price", 0)
            current_price = context.current_prices.get(symbol, 0)
            if peak_price <= 0 or current_price <= 0:
                continue

            stop_price = peak_price * (1.0 - self.trailing_pct)
            if current_price < stop_price:
                drawdown = (current_price - peak_price) / peak_price
                return RiskDecision(
                    approved=False,
                    reason=(
                        f"{symbol} 从最高价 {peak_price:.2f} 回撤 {drawdown:.2%}，"
                        f"触发 {self.trailing_pct:.0%} 移动止损"
                    ),
                    action="close_all",
                )

        return RiskDecision(approved=True)
