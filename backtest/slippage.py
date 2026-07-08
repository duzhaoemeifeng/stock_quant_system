"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。滑点模型使用固定比例近似，
 实际滑点可能因流动性等因素大幅偏离。
==================================================
滑点与手续费模拟模型。
"""

from dataclasses import dataclass


@dataclass
class SlippageModel:
    """A股滑点与手续费模拟。

    买入费用 = max(佣金比例 * 成交额, 最低佣金)
    卖出费用 = max(佣金比例 * 成交额, 最低佣金) + 印花税 * 成交额
    滑点 = 成交价 * 滑点比例

    params:
        slippage_pct: 滑点比例（默认 0.001 = 0.1%）。
        commission_pct: 佣金比例（默认 0.0003 = 万分之三）。
        min_commission: 最低佣金（默认 5.0 元）。
        stamp_tax_pct: 印花税比例（默认 0.001 = 千分之一，仅卖出）。
    """

    slippage_pct: float = 0.001
    commission_pct: float = 0.0003
    min_commission: float = 5.0
    stamp_tax_pct: float = 0.001

    def apply_buy(
        self, price: float, volume: int
    ) -> tuple[float, float]:
        """计算买入实际成交价和总费用。

        Args:
            price: 理论成交价。
            volume: 成交股数（必须是100的整数倍）。

        Returns:
            (actual_price, total_fee)
        """
        actual_price = price * (1.0 + self.slippage_pct)
        turnover = actual_price * volume
        commission = max(turnover * self.commission_pct, self.min_commission)
        return actual_price, commission

    def apply_sell(
        self, price: float, volume: int
    ) -> tuple[float, float]:
        """计算卖出实际成交价和总费用（含印花税）。

        Returns:
            (actual_price, total_fee)
        """
        actual_price = price * (1.0 - self.slippage_pct)
        turnover = actual_price * volume
        commission = max(turnover * self.commission_pct, self.min_commission)
        stamp_tax = turnover * self.stamp_tax_pct
        return actual_price, commission + stamp_tax

    def get_buy_cost_rate(self) -> float:
        """买入时总成本比例（估算）。"""
        return self.slippage_pct + self.commission_pct

    def get_sell_cost_rate(self) -> float:
        """卖出时总成本比例（估算）。"""
        return self.slippage_pct + self.commission_pct + self.stamp_tax_pct
