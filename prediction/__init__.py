"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。机器学习预测基于历史统计
 规律，市场条件变化可能导致预测模型失效。预测
 结果不可作为唯一交易决策依据。
==================================================
股票预测模块入口。
"""

import pandas as pd

from .base import BasePredictionModel, PredictionResult
from .features import FeatureEngineer
from .models import (
    RandomForestDirectionModel,
    GradientBoostingDirectionModel,
    LogisticDirectionModel,
    RandomForestReturnModel,
)
from .ensemble import VotingEnsembleModel
from .evaluation import PredictionEvaluator


class PredictionEngine:
    """预测引擎：特征 + 分类模型 + 回归模型 + 预测 编排器。

    对外暴露简洁的 train/predict 接口，Agent 和 UI 只需与此交互。
    """

    def __init__(self, model: BasePredictionModel | None = None):
        self.feature_engineer = FeatureEngineer()
        self.model = model or RandomForestDirectionModel()
        self.return_model = RandomForestReturnModel()  # 辅回归器，预测涨跌幅度
        self._is_trained = False
        self._last_metrics: dict = {}
        self._return_metrics: dict = {}
        self._last_X: pd.DataFrame | None = None
        self._last_close: float | None = None

    def train(self, data: pd.DataFrame) -> dict:
        """训练分类模型 + 回归模型，返回评估指标。

        Args:
            data: OHLCV DataFrame (date, open, high, low, close, volume)

        Returns:
            dict of evaluation metrics
        """
        X = self.feature_engineer.compute_features(data)
        y_cls = self.feature_engineer.compute_target(data)
        y_reg = self.feature_engineer.compute_target_regression(data)
        self._last_X = X
        self._last_close = float(data["close"].iloc[-1])

        # 删去含 NaN 的行
        valid = X.notna().all(axis=1) & y_cls.notna()
        X_valid = X.loc[valid]
        y_cls_valid = y_cls.loc[valid]
        y_reg_valid = y_reg.loc[valid]

        if len(X_valid) < 50:
            raise ValueError(f"训练数据不足：仅 {len(X_valid)} 条有效样本，至少需要 50 条")

        # 按时间切分：前 80% 训练，后 20% 验证
        split = int(len(X_valid) * 0.8)
        X_train, X_test = X_valid.iloc[:split], X_valid.iloc[split:]
        y_train, y_test = y_cls_valid.iloc[:split], y_cls_valid.iloc[split:]
        y_reg_train, y_reg_test = y_reg_valid.iloc[:split], y_reg_valid.iloc[split:]

        # 训练分类模型（涨跌方向）
        self.model.train(X_train, y_train)
        self._last_metrics = self.model.evaluate(X_test, y_test)

        # 训练回归模型（涨跌幅度）
        self.return_model.train(X_train, y_reg_train)
        self._return_metrics = self.return_model.evaluate(X_test, y_reg_test)

        self._is_trained = True

        return self._last_metrics

    def predict(self, data: pd.DataFrame) -> PredictionResult:
        """对最新一行数据做预测。未训练时自动调用 train()。

        Args:
            data: OHLCV DataFrame

        Returns:
            PredictionResult
        """
        if not self._is_trained:
            self.train(data)

        X = self._last_X
        close = self._last_close or float(data["close"].iloc[-1])

        if X is None:
            X = self.feature_engineer.compute_features(data)

        # 分类预测（方向）
        result = self.model.predict(X)

        # 回归预测（幅度 + 目标价）
        result.current_price = close

        ret_1d = self.return_model.predict_return(X)
        result.predicted_return_1d = round(ret_1d, 6)
        result.predicted_price_1d = round(close * (1 + ret_1d), 2)

        # 5日粗略估算（日收益 * 5，不做独立建模）
        ret_5d = ret_1d * 5
        result.predicted_return_5d = round(ret_5d, 6)
        result.predicted_price_5d = round(close * (1 + ret_5d), 2)

        return result

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    @property
    def last_metrics(self) -> dict:
        return self._last_metrics
