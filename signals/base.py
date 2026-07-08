"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
信号生成器抽象基类。

信号约定:
    +1 : 买入信号
    -1 : 卖出信号
     0 : 持仓不变
   NaN : 空仓/不交易
"""

from abc import ABC, abstractmethod

import pandas as pd


class SignalGenerator(ABC):
    """信号生成器抽象基类。

    所有信号生成策略均需继承此类并实现 generate 方法。
    输出 DataFrame 至少包含 'signal' 列，可选 'signal_strength' 列。
    """

    @abstractmethod
    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """生成交易信号。

        Args:
            data: 统一 Schema 的 OHLCV DataFrame。
            factors: 预计算的因子 DataFrame（可为 None）。

        Returns:
            DataFrame，index 与 data 对齐，包含:
                - signal: int, 交易信号 (+1/-1/0)
                - signal_strength: float, 可选，信号强度 [0, 1]
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
