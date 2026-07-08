"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
ATR 动态仓位模型：基于波动率调整仓位大小。
高波动 → 小仓位，低波动 → 大仓位。
"""

import pandas as pd

from .base import PositionSizer
from ..factors.technical import ATRFactor


class ATRPositionSizer(PositionSizer):
    """ATR 动态仓位计算器。

    params:
        risk_pct: 单笔愿意承担的风险比例（默认 0.02 = 2%）。
        atr_window: ATR 计算窗口（默认 14）。
        multiplier: ATR 倍数（默认 2.0）。

    目标股数 = capital * risk_pct / (ATR * multiplier)
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.risk_pct = self.params.get("risk_pct", 0.02)
        self.atr_window = self.params.get("atr_window", 14)
        self.multiplier = self.params.get("multiplier", 2.0)
        self._atr_factor = ATRFactor({"window": self.atr_window})

    def calculate(
        self,
        capital: float,
        price: float,
        signal_strength: float,
        data: pd.DataFrame | None = None,
    ) -> float:
        if price <= 0 or capital <= 0:
            return 0.0

        # 默认波动率估算
        atr_value = price * 0.02  # 假设2%波动

        if data is not None and len(data) > self.atr_window:
            atr_series = self._atr_factor.compute(data)
            latest_atr = atr_series.iloc[-1]
            if pd.notna(latest_atr) and latest_atr > 0:
                atr_value = latest_atr

        risk_amount = capital * self.risk_pct * signal_strength
        stop_distance = atr_value * self.multiplier
        shares = int(risk_amount / max(stop_distance, 0.01))
        return min(shares, int(capital * 0.25 / price))
