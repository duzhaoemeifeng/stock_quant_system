"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
预测评估工具 — classification metrics / regression metrics / 策略回测。
"""

import numpy as np
import pandas as pd


class PredictionEvaluator:
    """预测模型评估器。

    所有方法为静态方法，可直接调用无需实例化。
    """

    @staticmethod
    def classification_metrics(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> dict:
        """计算分类性能指标。

        Returns:
            dict with accuracy, precision, recall, f1, correct, total
        """
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

        return {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "correct": int(np.sum(np.array(y_true) == np.array(y_pred))),
            "total": len(y_true),
        }

    @staticmethod
    def regression_metrics(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> dict:
        """计算回归性能指标。

        Returns:
            dict with mse, rmse, mae, r2, direction_accuracy
        """
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        y_t = np.array(y_true)
        y_p = np.array(y_pred)

        # 方向准确率
        dir_true = (y_t > 0).astype(int)
        dir_pred = (y_p > 0).astype(int)
        dir_acc = float(np.mean(dir_true == dir_pred))

        return {
            "mse": round(float(mean_squared_error(y_t, y_p)), 6),
            "rmse": round(float(np.sqrt(mean_squared_error(y_t, y_p))), 6),
            "mae": round(float(mean_absolute_error(y_t, y_p)), 6),
            "r2": round(float(r2_score(y_t, y_p)), 4),
            "direction_accuracy": round(dir_acc, 4),
        }

    @staticmethod
    def rolling_accuracy(
        y_true: pd.Series,
        y_pred: pd.Series,
        window: int = 20,
    ) -> pd.Series:
        """计算滚动窗口准确率。

        Args:
            y_true: 真实标签
            y_pred: 预测标签
            window: 滚动窗口大小

        Returns:
            Series of rolling accuracy values
        """
        correct = (np.array(y_true) == np.array(y_pred)).astype(int)
        return pd.Series(correct).rolling(window=window, min_periods=window).mean()

    @staticmethod
    def backtest_prediction_strategy(
        data: pd.DataFrame,
        signals: pd.Series,
        initial_capital: float = 100000,
    ) -> dict:
        """基于预测信号的简单回测。

        Args:
            data: OHLCV DataFrame
            signals: 预测信号 (1=买入, 0=空仓)
            initial_capital: 初始资金

        Returns:
            dict with total_return, sharpe, max_drawdown, win_rate
        """
        close = data["close"].astype(float)
        returns = close.pct_change().shift(-1)  # 买入后次日收益

        # 按信号计算策略收益
        strategy_returns = returns * signals.shift(1)
        strategy_returns = strategy_returns.dropna()

        if len(strategy_returns) == 0:
            return {"total_return": 0, "sharpe": 0, "max_drawdown": 0, "win_rate": 0}

        # 累计收益
        equity = (1 + strategy_returns).cumprod()
        total_return = float(equity.iloc[-1] - 1) if len(equity) > 0 else 0.0

        # Sharpe
        ann_return = float(strategy_returns.mean() * 252)
        ann_vol = float(strategy_returns.std() * np.sqrt(252))
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0

        # Max drawdown
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        max_drawdown = float(drawdown.min()) if len(drawdown) > 0 else 1.0

        # Win rate
        wins = (strategy_returns > 0).sum()
        total_trades = len(strategy_returns)
        win_rate = float(wins / total_trades) if total_trades > 0 else 0.0

        return {
            "total_return": round(total_return, 4),
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 4),
            "win_rate": round(win_rate, 4),
            "n_trades": total_trades,
        }
