"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
仓位与风控抽象基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


class PositionSizer(ABC):
    """仓位计算器抽象基类。

    根据资金、价格、信号强度计算目标持仓数量。
    返回正值表示买入，负值表示卖出。
    """

    @abstractmethod
    def calculate(
        self,
        capital: float,
        price: float,
        signal_strength: float,
        data: pd.DataFrame | None = None,
    ) -> float:
        """计算目标持仓股数。

        Args:
            capital: 当前可用资金。
            price: 当前成交价。
            signal_strength: 信号强度 [0, 1]。
            data: 可选的历史数据（ATR 等方法需要）。

        Returns:
            目标持仓股数（正数买入，负数卖出，0不操作）。
        """
        ...


# ---- 风控 ----

@dataclass
class RiskContext:
    """风控上下文：当前账户状态与市场数据。"""
    current_capital: float
    peak_capital: float
    positions: dict = field(default_factory=dict)
    daily_pnl: float = 0.0
    daily_start_capital: float = 0.0
    total_trades_today: int = 0
    consecutive_losses: int = 0
    current_prices: dict = field(default_factory=dict)


@dataclass
class RiskDecision:
    """风控决策。"""
    approved: bool = True
    reason: str | None = None
    action: str | None = None  # "close_all" | "halt_trading" | "reduce"


class RiskRule(ABC):
    """风控规则抽象基类。"""

    @abstractmethod
    def check(self, context: RiskContext) -> RiskDecision:
        """检查当前账户状态是否通过此规则。

        Args:
            context: 风控上下文。

        Returns:
            RiskDecision，包含是否通过及拒绝原因。
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
