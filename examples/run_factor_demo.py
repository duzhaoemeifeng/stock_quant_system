"""
==================================================
 风险提示：本脚本仅用于量化策略学习与教学演示，
 不构成任何投资建议。
==================================================
因子库使用示例：展示如何注册自定义因子并使用所有内置因子。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from factors.registry import FactorRegistry
from factors.base import Factor

# 确保内置因子已注册
from factors import technical, momentum, volatility  # noqa: F401


class CustomMomentumFactor(Factor):
    """自定义动量因子：20日动量除以20日波动率。"""

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.window = self.params.get("window", 20)

    def compute(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].astype(float)
        momentum = close / close.shift(self.window) - 1.0
        vol = close.pct_change().rolling(self.window).std()
        return momentum / (vol + 1e-12)


# 注册自定义因子
FactorRegistry.register(CustomMomentumFactor)


def main():
    print("=== 因子库使用示例 ===\n")

    # 列出所有已注册因子
    factors = FactorRegistry.list_factors()
    print(f"已注册因子 ({len(factors)}):")
    for f in factors:
        print(f"  - {f}")

    # 创建因子实例
    print("\n创建因子实例:")
    sma = FactorRegistry.create("SMAFactor", {"window": 20})
    print(f"  SMA: {sma}")

    rsi = FactorRegistry.create("RSIFactor", {"window": 14})
    print(f"  RSI: {rsi}")

    custom = FactorRegistry.create("CustomMomentumFactor", {"window": 20})
    print(f"  自定义: {custom}")


if __name__ == "__main__":
    main()
