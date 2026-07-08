"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。以下为实盘交易接口定义，
 不包含任何券商 API 的具体实现。
==================================================
实盘交易接口抽象定义。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    """订单数据模型。"""
    symbol: str
    side: str            # "buy" | "sell"
    order_type: str      # "market" | "limit"
    quantity: float
    price: float | None = None
    time_in_force: str = "day"


@dataclass
class Position:
    """持仓数据模型。"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class AccountInfo:
    """账户信息。"""
    total_assets: float = 0.0
    available_cash: float = 0.0
    market_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0


class LiveTrader(ABC):
    """实盘交易接口抽象基类。

    风险提示：实盘交易涉及真实资金，存在本金损失风险。
    本系统不提供任何实盘接入的完整实现。
    实际使用前请充分测试并在模拟环境中验证。
    """

    @abstractmethod
    def connect(self) -> bool:
        """建立连接。"""
        ...

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接。"""
        ...

    @abstractmethod
    def place_order(self, order: Order) -> str:
        """下单。

        Returns:
            订单ID。
        """
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        ...

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """查询当前持仓。"""
        ...

    @abstractmethod
    def get_account(self) -> AccountInfo:
        """查询账户信息。"""
        ...
