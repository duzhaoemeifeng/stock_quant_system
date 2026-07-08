"""
==================================================
 风险提示：本脚本仅用于量化策略学习与教学演示，
 不构成任何投资建议。
==================================================
实盘接口使用演示（桩代码）。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from live import LiveTrader, Order, Position, AccountInfo


class StubTrader(LiveTrader):
    """实盘接口桩实现（用于测试流程）。"""

    def __init__(self):
        self._connected = False
        self._orders: dict[str, Order] = {}
        self._positions: dict[str, Position] = {}

    def connect(self) -> bool:
        print("[桩] 连接成功")
        self._connected = True
        return True

    def disconnect(self) -> bool:
        print("[桩] 断开连接")
        self._connected = False
        return True

    def place_order(self, order: Order) -> str:
        oid = f"ORD-{len(self._orders):04d}"
        self._orders[oid] = order
        print(f"[桩] 下单: {order.side} {order.quantity}股 {order.symbol} @ {order.price}")
        return oid

    def cancel_order(self, order_id: str) -> bool:
        print(f"[桩] 撤单: {order_id}")
        return True

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_account(self) -> AccountInfo:
        return AccountInfo(
            total_assets=1_000_000,
            available_cash=500_000,
            market_value=500_000,
        )


def main():
    print("=== 实盘接口演示（桩模式）===\n")

    trader = StubTrader()
    trader.connect()

    order = Order(
        symbol="000001",
        side="buy",
        order_type="limit",
        quantity=1000,
        price=12.50,
    )
    oid = trader.place_order(order)
    print(f"  订单ID: {oid}")

    account = trader.get_account()
    print(f"  总资产: {account.total_assets:,.0f}")
    print(f"  可用资金: {account.available_cash:,.0f}")

    trader.disconnect()
    print("\n风险提示：此为桩代码演示，不可用于实盘交易。")


if __name__ == "__main__":
    main()
