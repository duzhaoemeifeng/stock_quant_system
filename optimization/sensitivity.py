"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
参数敏感性分析模块。
"""

import numpy as np
import pandas as pd

from ..backtest.base import BacktestEngine


class SensitivityAnalyzer:
    """参数敏感性分析器。

    逐一变化目标参数，固定其他参数，观察绩效指标变化。
    用于识别哪些参数对结果影响最大（杠杆效应）。

    使用方法:
        analyzer = SensitivityAnalyzer(engine)
        results = analyzer.analyze(
            data, signal_fn, base_params, "fast_window",
            param_range=[3, 5, 10, 15, 20]
        )
    """

    def __init__(self, engine: BacktestEngine):
        self.engine = engine

    def analyze(
        self,
        data: pd.DataFrame,
        signal_fn,
        base_params: dict,
        param_name: str,
        param_range: list,
        position_sizer=None,
        risk_manager=None,
        slippage_model=None,
        initial_capital: float = 1_000_000.0,
    ) -> pd.DataFrame:
        """对单个参数进行敏感性扫描。

        Args:
            data: OHLCV 数据。
            signal_fn: 信号生成函数 fn(data, params) -> DataFrame。
            base_params: 基准参数。
            param_name: 要分析变化的参数名。
            param_range: 参数取值列表。
            position_sizer: 仓位计算器。
            risk_manager: 风控管理器。
            slippage_model: 滑点模型。
            initial_capital: 初始资金。

        Returns:
            DataFrame，每行一个参数值，包含所有绩效指标。
        """
        results = []
        for val in param_range:
            params = {**base_params, param_name: val}
            try:
                signals = signal_fn(data, params)
                bt = self.engine.run(
                    data=data, signals=signals,
                    position_sizer=position_sizer,
                    risk_manager=risk_manager,
                    slippage_model=slippage_model,
                    initial_capital=initial_capital,
                )
                results.append({
                    param_name: val,
                    "sharpe_ratio": bt.sharpe_ratio,
                    "total_return": bt.total_return,
                    "annual_return": bt.annual_return,
                    "max_drawdown": bt.max_drawdown,
                    "calmar_ratio": bt.calmar_ratio,
                    "win_rate": bt.win_rate,
                    "profit_factor": bt.profit_factor,
                    "trade_count": bt.trade_count,
                })
            except Exception:
                continue
        return pd.DataFrame(results)

    def tornado_data(
        self,
        sensitivity_results: dict[str, pd.DataFrame],
        metric: str = "sharpe_ratio",
    ) -> pd.DataFrame:
        """生成 Tornado 图数据。

        Args:
            sensitivity_results: {param_name: sensitivity_df}。
            metric: 关注的绩效指标。

        Returns:
            DataFrame，每行一个参数，包含 low/high/range。
        """
        rows = []
        for param_name, df in sensitivity_results.items():
            if df.empty or metric not in df.columns:
                continue
            low_val = df[metric].min()
            high_val = df[metric].max()
            base_val = df[metric].iloc[len(df) // 2] if len(df) > 2 else df[metric].mean()
            rows.append({
                "parameter": param_name,
                "low": low_val,
                "high": high_val,
                "base": base_val,
                "range": high_val - low_val,
            })
        result = pd.DataFrame(rows)
        result = result.sort_values("range", ascending=True)
        return result
