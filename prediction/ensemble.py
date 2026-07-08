"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
集成模型 — 多模型加权投票。
"""

import numpy as np
import pandas as pd

from .base import BasePredictionModel, PredictionResult
from .models import (
    RandomForestDirectionModel,
    GradientBoostingDirectionModel,
    LogisticDirectionModel,
)


class VotingEnsembleModel(BasePredictionModel):
    """加权投票集成模型。

    组合多个模型，按权重对预测概率加权平均。
    默认使用 RF + GBDT + LR 三个模型等权投票。
    """

    def __init__(
        self,
        models: list[BasePredictionModel] | None = None,
        weights: list[float] | None = None,
    ):
        self._models = models or [
            RandomForestDirectionModel(),
            GradientBoostingDirectionModel(),
            LogisticDirectionModel(),
        ]
        if weights is None:
            self._weights = [1.0 / len(self._models)] * len(self._models)
        else:
            total = sum(weights)
            self._weights = [w / total for w in weights]

        self._trained = False
        self._feature_names: list[str] = []
        self._last_metrics: dict = {}

    @property
    def name(self) -> str:
        parts = [m.name for m in self._models]
        return f"Ensemble({', '.join(parts)})"

    @property
    def trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._feature_names = list(X.columns)
        for model in self._models:
            model.train(X, y)
        self._trained = True

    def predict(self, X: pd.DataFrame) -> PredictionResult:
        if not self._trained:
            return PredictionResult(
                symbol="",
                date=pd.Timestamp.now(),
                direction=0,
                warning="模型未训练，无预测结果",
            )

        row = X.iloc[[-1]]
        weighted_prob = 0.0
        all_feature_importances: dict[str, float] = {}

        for model, weight in zip(self._models, self._weights):
            model_pred = model.predict(X)
            weighted_prob += model_pred.direction_probability * weight
            for feat, imp in model.feature_importance.items():
                all_feature_importances[feat] = all_feature_importances.get(feat, 0) + imp * weight

        # 排序取 top 10
        sorted_importances = dict(
            sorted(all_feature_importances.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        direction = 1 if weighted_prob >= 0.5 else -1
        direction_prob = weighted_prob if direction == 1 else 1 - weighted_prob
        confidence = max(direction_prob, 1 - direction_prob)

        return PredictionResult(
            symbol="",
            date=X.index[-1] if hasattr(X.index[-1], "strftime") else pd.Timestamp.now(),
            direction=direction,
            direction_probability=round(float(weighted_prob if direction == 1 else 1 - weighted_prob), 4),
            direction_label="上涨" if direction == 1 else "下跌",
            confidence=round(float(confidence), 4),
            feature_importance=sorted_importances,
            model_name=self.name,
            is_trained=True,
            evaluation_metrics=self._last_metrics,
        )

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        # 集成预测全部测试集
        y_prob = np.zeros(len(X_test))
        for model, weight in zip(self._models, self._weights):
            # 需要获取各模型对 X_test 的概率预测
            row_by_row = []
            for i in range(len(X_test)):
                pred = model.predict(X_test.iloc[[i]])
                row_by_row.append(pred.direction_probability)
            y_prob += np.array(row_by_row) * weight

        y_pred = (y_prob >= 0.5).astype(int)

        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "n_samples": len(y_test),
        }
        self._last_metrics = metrics
        return metrics

    @property
    def feature_importance(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for model, weight in zip(self._models, self._weights):
            for feat, imp in model.feature_importance.items():
                result[feat] = result.get(feat, 0) + imp * weight
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
