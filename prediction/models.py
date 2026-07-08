"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
ML 预测模型实现 — RandomForest / GradientBoosting / LogisticRegression。
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from .base import BasePredictionModel, PredictionResult


class RandomForestDirectionModel(BasePredictionModel):
    """随机森林涨跌分类模型。

    默认参数针对金融数据优化：较多树、限制深度防过拟合。
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self._params = {
            "n_estimators": p.get("n_estimators", 200),
            "max_depth": p.get("max_depth", 8),
            "min_samples_leaf": p.get("min_samples_leaf", 5),
            "random_state": p.get("random_state", 42),
            "n_jobs": -1,
        }
        self._model = RandomForestClassifier(**self._params)
        self._feature_names: list[str] = []
        self._trained = False
        self._last_metrics: dict = {}

    @property
    def name(self) -> str:
        return "RandomForest"

    @property
    def trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._feature_names = list(X.columns)
        self._model.fit(X, y)
        self._trained = True

    def predict(self, X: pd.DataFrame) -> PredictionResult:
        if not self._trained:
            return PredictionResult(
                symbol="",
                date=pd.Timestamp.now(),
                direction=0,
                warning="模型未训练，无预测结果",
            )

        # 只用 X 的最后一行做预测
        row = X.iloc[[-1]]
        prob = self._model.predict_proba(row)[0]
        pred_class = int(self._model.predict(row)[0])

        direction = 1 if pred_class == 1 else -1
        prob_up = prob[1] if len(prob) > 1 else prob[0]

        # 置信度：当概率在 0.5-0.7 为中，0.7-0.85 为高，>0.85 为极高
        confidence = min(prob_up, 1.0) if direction == 1 else min(1 - prob_up, 1.0)

        # 特征重要性
        importances = dict(
            sorted(
                zip(self._feature_names, self._model.feature_importances_),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        )

        return PredictionResult(
            symbol="",
            date=X.index[-1] if hasattr(X.index[-1], "strftime") else pd.Timestamp.now(),
            direction=direction,
            direction_probability=round(float(prob_up), 4),
            direction_label="上涨" if direction == 1 else "下跌",
            confidence=round(float(confidence), 4),
            feature_importance=importances,
            model_name=self.name,
            is_trained=True,
            evaluation_metrics=self._last_metrics,
        )

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        y_pred = self._model.predict(X_test)
        y_prob = self._model.predict_proba(X_test)[:, 1] if hasattr(self._model, "predict_proba") else None

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
        if not self._trained:
            return {}
        return dict(zip(self._feature_names, self._model.feature_importances_))


class GradientBoostingDirectionModel(BasePredictionModel):
    """梯度提升涨跌分类模型。

    精度通常略高于 RF，但对参数更敏感。
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self._params = {
            "n_estimators": p.get("n_estimators", 100),
            "learning_rate": p.get("learning_rate", 0.05),
            "max_depth": p.get("max_depth", 4),
            "random_state": p.get("random_state", 42),
        }
        self._model = GradientBoostingClassifier(**self._params)
        self._feature_names: list[str] = []
        self._trained = False
        self._last_metrics: dict = {}

    @property
    def name(self) -> str:
        return "GradientBoosting"

    @property
    def trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._feature_names = list(X.columns)
        self._model.fit(X, y)
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
        prob = self._model.predict_proba(row)[0]
        pred_class = int(self._model.predict(row)[0])

        direction = 1 if pred_class == 1 else -1
        prob_up = prob[1] if len(prob) > 1 else prob[0]
        confidence = min(prob_up, 1.0) if direction == 1 else min(1 - prob_up, 1.0)

        importances = dict(
            sorted(
                zip(self._feature_names, self._model.feature_importances_),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        )

        return PredictionResult(
            symbol="",
            date=X.index[-1] if hasattr(X.index[-1], "strftime") else pd.Timestamp.now(),
            direction=direction,
            direction_probability=round(float(prob_up), 4),
            direction_label="上涨" if direction == 1 else "下跌",
            confidence=round(float(confidence), 4),
            feature_importance=importances,
            model_name=self.name,
            is_trained=True,
            evaluation_metrics=self._last_metrics,
        )

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        y_pred = self._model.predict(X_test)
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
        if not self._trained:
            return {}
        return dict(zip(self._feature_names, self._model.feature_importances_))


class LogisticDirectionModel(BasePredictionModel):
    """逻辑回归涨跌分类模型 — 可解释性基线。

    线性模型，可作为对照基准评估复杂模型是否有增益。
    """

    def __init__(self, params: dict | None = None):
        p = params or {}
        self._params = {
            "C": p.get("C", 1.0),
            "max_iter": p.get("max_iter", 1000),
            "penalty": p.get("penalty", "l2"),
            "random_state": p.get("random_state", 42),
        }
        self._model = LogisticRegression(**self._params)
        self._feature_names: list[str] = []
        self._trained = False
        self._last_metrics: dict = {}

    @property
    def name(self) -> str:
        return "LogisticRegression"

    @property
    def trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._feature_names = list(X.columns)
        self._model.fit(X, y)
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
        prob = self._model.predict_proba(row)[0]
        pred_class = int(self._model.predict(row)[0])

        direction = 1 if pred_class == 1 else -1
        prob_up = prob[1] if len(prob) > 1 else prob[0]
        confidence = min(prob_up, 1.0) if direction == 1 else min(1 - prob_up, 1.0)

        # LR 特征重要性 = 系数绝对值归一化
        coef = np.abs(self._model.coef_[0])
        coef_norm = coef / (coef.sum() + 1e-12)
        importances = dict(
            sorted(
                zip(self._feature_names, coef_norm),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        )

        return PredictionResult(
            symbol="",
            date=X.index[-1] if hasattr(X.index[-1], "strftime") else pd.Timestamp.now(),
            direction=direction,
            direction_probability=round(float(prob_up), 4),
            direction_label="上涨" if direction == 1 else "下跌",
            confidence=round(float(confidence), 4),
            feature_importance=importances,
            model_name=self.name,
            is_trained=True,
            evaluation_metrics=self._last_metrics,
        )

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        y_pred = self._model.predict(X_test)
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
        if not self._trained:
            return {}
        coef = np.abs(self._model.coef_[0])
        return dict(zip(self._feature_names, coef / (coef.sum() + 1e-12)))


class RandomForestReturnModel:
    """随机森林收益率回归模型。

    预测次日/5日涨跌幅度（百分比），用于计算目标价位。
    非 BasePredictionModel 子类，作为辅助回归器使用。
    """

    def __init__(self, params: dict | None = None):
        from sklearn.ensemble import RandomForestRegressor

        p = params or {}
        self._params = {
            "n_estimators": p.get("n_estimators", 150),
            "max_depth": p.get("max_depth", 8),
            "min_samples_leaf": p.get("min_samples_leaf", 5),
            "random_state": p.get("random_state", 42),
            "n_jobs": -1,
        }
        self._model = RandomForestRegressor(**self._params)
        self._trained = False
        self._last_metrics: dict = {}

    @property
    def name(self) -> str:
        return "RandomForestRegressor"

    @property
    def trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._model.fit(X, y)
        self._trained = True

    def predict_return(self, X: pd.DataFrame) -> float:
        """预测最新一行的收益率。"""
        if not self._trained:
            return 0.0
        return float(self._model.predict(X.iloc[[-1]])[0])

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        y_pred = self._model.predict(X_test)
        y_t = np.array(y_test)
        y_p = np.array(y_pred)

        dir_acc = float(np.mean((y_t > 0) == (y_p > 0)))

        return {
            "rmse": round(float(np.sqrt(mean_squared_error(y_t, y_p))), 6),
            "mae": round(float(mean_absolute_error(y_t, y_p)), 6),
            "r2": round(float(r2_score(y_t, y_p)), 4),
            "direction_accuracy": round(dir_acc, 4),
            "n_samples": len(y_test),
        }
