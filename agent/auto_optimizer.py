"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
自动参数优化 Agent — 自动搜索最佳策略参数组合。
"""

import itertools

import numpy as np
import pandas as pd


class AutoOptimizer:
    """自动参数优化器。

    对指定策略执行网格搜索，找到最优参数组合。
    支持样本内/外分割验证，避免过拟合。

    使用方法:
        opt = AutoOptimizer()
        result = opt.optimize(data, strategy_fn, param_grid)
    """

    def __init__(self, scoring: str = "sharpe_ratio", cv_fold: int = 0):
        self.scoring = scoring
        self.cv_fold = cv_fold  # 0 = 不交叉验证

    def optimize(
        self,
        data: pd.DataFrame,
        strategy_fn,
        param_grid: dict[str, list],
        in_sample_ratio: float = 0.7,
    ) -> dict:
        """执行自动参数优化。

        Args:
            data: OHLCV 数据。
            strategy_fn: 策略函数 fn(data, params) -> signals_df。
            param_grid: 参数网格 {"param": [v1, v2, ...]}。
            in_sample_ratio: 样本内比例。

        Returns:
            dict 包含: best_params, best_score, all_results, top5, sensitivity
        """
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        n = len(data)
        split_idx = int(n * in_sample_ratio)
        in_sample = data.iloc[:split_idx]
        out_sample = data.iloc[split_idx:]

        all_results = []
        for combo in combinations:
            params = dict(zip(param_names, combo))
            try:
                # 样本内
                signals_in = strategy_fn(in_sample, params)
                metrics_in = self._evaluate(in_sample, signals_in)

                # 样本外
                signals_out = strategy_fn(out_sample, params)
                metrics_out = self._evaluate(out_sample, signals_out)

                row = {**params,
                       "sharpe_in": metrics_in["sharpe"],
                       "sharpe_out": metrics_out["sharpe"],
                       "return_in": metrics_in["total_return"],
                       "return_out": metrics_out["total_return"],
                       "max_dd_in": metrics_in["max_dd"],
                       "max_dd_out": metrics_out["max_dd"],
                       "sharpe_drop": metrics_out["sharpe"] - metrics_in["sharpe"],
                       }
                all_results.append(row)
            except Exception:
                continue

        if not all_results:
            return {"best_params": {}, "best_score": 0, "error": "优化无结果"}

        df = pd.DataFrame(all_results)

        # 综合评分：样本外夏普优先，考虑夏普衰减惩罚
        df["score"] = df["sharpe_out"] - abs(df["sharpe_drop"]) * 0.5
        df = df.sort_values("score", ascending=False).reset_index(drop=True)

        best_row = df.iloc[0]
        best_params = {k: best_row[k] for k in param_names}

        # 敏感性：每个参数的最大得分-最小得分
        sensitivity = {}
        for p in param_names:
            grouped = df.groupby(p)["score"].agg(["max", "min"]).reset_index()
            sensitivity[p] = abs(grouped["max"] - grouped["min"]).mean()

        return {
            "best_params": best_params,
            "best_score": best_row["score"],
            "best_sharpe_in": best_row["sharpe_in"],
            "best_sharpe_out": best_row["sharpe_out"],
            "sharpe_drop": best_row["sharpe_drop"],
            "is_overfitted": best_row["sharpe_drop"] < -0.5,
            "top5": df.head(5).to_dict("records"),
            "all_results": df,
            "sensitivity": sensitivity,
            "n_tested": len(df),
        }

    def _evaluate(self, data: pd.DataFrame, signals_df: pd.DataFrame) -> dict:
        """简化版回测评估。"""
        close = data["close"].values
        n = len(data)

        signal_arr = signals_df["signal"].values if "signal" in signals_df.columns else np.zeros(n)
        pos = 0
        equity = np.zeros(n)
        equity[0] = 1000000
        cash = 1000000
        trades_pnl = []

        for i in range(1, n):
            sig = signal_arr[i]
            price = close[i]
            if pd.notna(sig):
                if sig > 0 and pos == 0:
                    shares = int(cash * 0.1 / price)
                    shares = (shares // 100) * 100
                    if shares >= 100:
                        cost = price * shares * 1.001  # 含滑点
                        if cost <= cash:
                            cash -= cost
                            pos = shares
                            entry_price = price
                elif sig < 0 and pos > 0:
                    proceeds = price * pos * 0.999
                    cash += proceeds
                    trades_pnl.append((price - entry_price) * pos)
                    pos = 0
            equity[i] = cash + pos * price

        eq = pd.Series(equity, index=data.index)
        rets = eq.pct_change().dropna()

        sharpe = (rets.mean() * 252 - 0.03) / (rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
        total_ret = (equity[-1] / equity[0]) - 1
        peak = np.maximum.accumulate(equity)
        max_dd = np.min((equity - peak) / peak)

        return {
            "sharpe": sharpe,
            "total_return": total_ret,
            "max_dd": max_dd,
            "n_trades": len(trades_pnl),
            "win_rate": np.mean([p > 0 for p in trades_pnl]) if trades_pnl else 0,
        }
