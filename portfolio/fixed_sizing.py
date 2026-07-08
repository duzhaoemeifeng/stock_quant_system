"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
固定仓位模型。
"""

import pandas as pd

from .base import PositionSizer


class FixedFractionSizer(PositionSizer):
    """固定资金比例仓位。

    params:
        fraction: 每次交易使用资金的比例（默认 0.1 = 10%）。

    目标股数 = capital * fraction * signal_strength / price
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.fraction = self.params.get("fraction", 0.10)
        self.max_fraction = self.params.get("max_fraction", 0.25)

    def calculate(
        self,
        capital: float,
        price: float,
        signal_strength: float,
        data: pd.DataFrame | None = None,
    ) -> float:
        if price <= 0 or capital <= 0:
            return 0.0

        effective_fraction = min(self.fraction * signal_strength, self.max_fraction)
        target_amount = capital * effective_fraction
        return int(target_amount / price)


class FixedSharesSizer(PositionSizer):
    """固定股数仓位。

    params:
        shares: 每次交易的固定股数（默认 100）。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.shares = self.params.get("shares", 100)

    def calculate(
        self,
        capital: float,
        price: float,
        signal_strength: float,
        data: pd.DataFrame | None = None,
    ) -> float:
        if price <= 0 or capital <= 0:
            return 0.0
        return min(self.shares, int(capital * 0.25 / price))
