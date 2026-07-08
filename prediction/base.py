"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
预测模块基类 — PredictionResult 数据结构 + BasePredictionModel ABC。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PredictionResult:
    """预测结果统一容器。"""

    symbol: str
    date: pd.Timestamp
    direction: int = 0              # 1=上涨, -1=下跌, 0=震荡
    direction_probability: float = 0.5  # 预测概率 [0, 1]
    direction_label: str = "震荡"
    current_price: float | None = None           # 当前收盘价
    predicted_return_1d: float | None = None     # 预测1日收益率
    predicted_return_5d: float | None = None     # 预测5日收益率
    predicted_price_1d: float | None = None      # 预测1日目标价
    predicted_price_5d: float | None = None      # 预测5日目标价
    confidence: float = 0.0         # 置信度评分 [0, 1]
    feature_importance: dict[str, float] = field(default_factory=dict)
    model_name: str = "unknown"
    is_trained: bool = False
    evaluation_metrics: dict = field(default_factory=dict)
    warning: str = "预测结果基于历史统计规律，不构成投资建议"


class BasePredictionModel(ABC):
    """预测模型抽象基类。

    所有模型统一接口: train → predict → evaluate。
    """

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """训练模型。"""
        ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> PredictionResult:
        """对 X 的最后一行做预测，返回 PredictionResult。"""
        ...

    @abstractmethod
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """评估模型，返回 metrics dict (accuracy, precision, recall, f1)。"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称。"""
        ...

    @property
    def feature_importance(self) -> dict[str, float]:
        """特征重要性，默认实现返回空 dict。"""
        return {}
