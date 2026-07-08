"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。网格搜索可能加剧过拟合风险。
 在参数空间过大时，随机搜索或贝叶斯优化更为合适。
==================================================
超参数网格搜索模块。
"""

import itertools
from dataclasses import dataclass, field

import pandas as pd
from tqdm import tqdm

from ..backtest.base import BacktestEngine


@dataclass
class GridSearchResult:
    """网格搜索结果。"""
    results_df: pd.DataFrame           # 每行一个参数组合 + 绩效指标
    best_params: dict = field(default_factory=dict)
    best_score: float = 0.0
    param_grid: dict = field(default_factory=dict)
    scoring: str = "sharpe_ratio"

    def top_n(self, n: int = 10) -> pd.DataFrame:
        """返回得分前 N 的参数组合。"""
        metric_col = self._metric_col()
        if metric_col and metric_col in self.results_df.columns:
            ascending = metric_col in ("max_drawdown",)
            return self.results_df.nsmallest(n, metric_col) if ascending else self.results_df.nlargest(n, metric_col)
        return self.results_df.head(n)

    def _metric_col(self) -> str:
        """scoring 名称到 DataFrame 列名的映射。"""
        return self.scoring


class GridSearch:
    """超参数网格搜索。

    使用方法:
        search = GridSearch(engine, param_grid, scoring="sharpe_ratio")
        result = search.search(data, signal_generator_fn, sizer, risk)
        print(result.top_n(5))
    """

    def __init__(
        self,
        engine: BacktestEngine,
        param_grid: dict[str, list],
        scoring: str = "sharpe_ratio",
    ):
        """
        Args:
            engine: 回测引擎实例。
            param_grid: 参数网格, {"param_name": [v1, v2, ...]}。
            scoring: 优化目标指标名。
        """
        self.engine = engine
        self.param_grid = param_grid
        self.scoring = scoring

    def search(
        self,
        data: pd.DataFrame,
        signal_fn,
        position_sizer,
        risk_manager=None,
        slippage_model=None,
        initial_capital: float = 1_000_000.0,
        static_params: dict | None = None,
    ) -> GridSearchResult:
        """执行网格搜索。

        Args:
            data: OHLCV 数据。
            signal_fn: 信号生成函数，签名为 fn(data, params) -> DataFrame。
            position_sizer: 仓位计算器。
            risk_manager: 风控管理器。
            slippage_model: 滑点模型。
            initial_capital: 初始资金。
            static_params: 不参与搜索的固定参数。

        Returns:
            GridSearchResult。
        """
        static = static_params or {}
        param_names = list(self.param_grid.keys())
        param_values = list(self.param_grid.values())
        combinations = list(itertools.product(*param_values))

        results = []
        progress = tqdm(combinations, desc="网格搜索")

        for combo in progress:
            params = dict(zip(param_names, combo))
            full_params = {**static, **params}

            try:
                signals = signal_fn(data, full_params)
                bt_result = self.engine.run(
                    data=data,
                    signals=signals,
                    position_sizer=position_sizer,
                    risk_manager=risk_manager,
                    slippage_model=slippage_model,
                    initial_capital=initial_capital,
                )
                score = self._extract_score(bt_result)
                row = {**params, self.scoring: score}
                # 附加核心指标
                row.update({
                    "total_return": bt_result.total_return,
                    "sharpe_ratio": bt_result.sharpe_ratio,
                    "max_drawdown": bt_result.max_drawdown,
                    "win_rate": bt_result.win_rate,
                    "trade_count": bt_result.trade_count,
                })
                results.append(row)
                progress.set_postfix({self.scoring: f"{score:.3f}"})
            except Exception:
                continue

        if not results:
            return GridSearchResult(
                results_df=pd.DataFrame(),
                param_grid=self.param_grid,
                scoring=self.scoring,
            )

        df = pd.DataFrame(results)
        # 按得分降序（max_drawdown 升序）
        ascending = self.scoring in ("max_drawdown",)
        df = df.sort_values(self.scoring, ascending=ascending).reset_index(drop=True)

        best_row = df.iloc[0]
        best_params = {k: best_row[k] for k in param_names}

        return GridSearchResult(
            results_df=df,
            best_params=best_params,
            best_score=best_row[self.scoring],
            param_grid=self.param_grid,
            scoring=self.scoring,
        )

    def _extract_score(self, bt_result) -> float:
        """从 BacktestResult 中提取评分指标。"""
        mapping = {
            "sharpe_ratio": bt_result.sharpe_ratio,
            "total_return": bt_result.total_return,
            "annual_return": bt_result.annual_return,
            "calmar_ratio": bt_result.calmar_ratio,
            "max_drawdown": bt_result.max_drawdown,
            "win_rate": bt_result.win_rate,
            "profit_factor": bt_result.profit_factor,
        }
        return mapping.get(self.scoring, bt_result.sharpe_ratio)
