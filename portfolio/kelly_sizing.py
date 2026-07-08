"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。凯利公式基于历史胜率和盈亏比
 计算最优仓位，但历史统计可能偏离未来实际。
==================================================
凯利公式仓位模型。
"""

import pandas as pd

from .base import PositionSizer


class KellyPositionSizer(PositionSizer):
    """凯利公式仓位计算器。

    params:
        win_rate: 历史胜率（默认 0.45）。
        win_loss_ratio: 盈亏比（默认 2.0）。
        fraction: 凯利分数倍率（默认 0.25，即1/4凯利）。
        max_position_pct: 最大仓位比例（默认 0.20）。

    f* = p - (1-p) / b  其中 p=胜率, b=盈亏比(盈利/亏损)
    实际仓位 = f* * fraction * signal_strength * capital / price
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.win_rate = self.params.get("win_rate", 0.45)
        self.win_loss_ratio = self.params.get("win_loss_ratio", 2.0)
        self.fraction = self.params.get("fraction", 0.25)
        self.max_position_pct = self.params.get("max_position_pct", 0.20)

    def calculate(
        self,
        capital: float,
        price: float,
        signal_strength: float,
        data: pd.DataFrame | None = None,
    ) -> float:
        if price <= 0 or capital <= 0:
            return 0.0

        p = max(0.01, min(0.99, self.win_rate))
        b = max(0.1, self.win_loss_ratio)
        kelly_f = p - (1.0 - p) / b

        # 凯利值为负时不交易
        if kelly_f <= 0:
            return 0.0

        # 分数凯利 + 信号强度调节
        effective_f = kelly_f * self.fraction * signal_strength
        effective_f = min(effective_f, self.max_position_pct)

        return int(capital * effective_f / price)
