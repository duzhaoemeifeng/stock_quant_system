"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
因子/技术指标抽象基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


class Factor(ABC):
    """所有技术指标因子的抽象基类。

    每个因子接收 OHLCV DataFrame，输出一个 Series。
    通过 params 字典配置可调参数，方便网格搜索。

    使用方法:
        class MyFactor(Factor):
            def compute(self, data: pd.DataFrame) -> pd.Series:
                return data['close'].rolling(20).mean()
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self._name: str = self.__class__.__name__

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        ...

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({params_str})"


@dataclass
class FactorResult:
    """因子计算结果容器。"""
    name: str
    series: pd.Series
    params: dict = field(default_factory=dict)
