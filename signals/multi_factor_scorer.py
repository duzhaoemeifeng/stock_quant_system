"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。多因子打分模型依赖历史因子
 的有效性，因子衰变可能导致策略失效。
==================================================
多因子加权打分引擎。
"""

import numpy as np
import pandas as pd

from .base import SignalGenerator
from ..factors.registry import FactorRegistry


class MultiFactorScorer(SignalGenerator):
    """多因子加权打分系统。

    将多个因子标准化后加权求和，得到综合得分。
    通过阈值将得分转换为买卖信号。

    params:
        weights: dict[str, float]，因子名称→权重。
        normalize: "zscore" | "rank" | "minmax"（默认 "zscore"）。
        buy_threshold: 买入阈值（得分 > 此值产生买入信号，默认 0.5）。
        sell_threshold: 卖出阈值（得分 < 此值产生卖出信号，默认 -0.5）。
    """

    def __init__(self, params: dict | None = None):
        self.params = params or {}
        self.weights: dict[str, float] = self.params.get("weights", {})
        self.normalize: str = self.params.get("normalize", "zscore")
        self.buy_threshold: float = self.params.get("buy_threshold", 0.5)
        self.sell_threshold: float = self.params.get("sell_threshold", -0.5)

    def generate(
        self,
        data: pd.DataFrame,
        factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """生成多因子打分信号。

        如果未提供预计算的 factors，则从注册中心自动计算。
        """
        if factors is None and self.weights:
            factors = self._compute_factors(data)

        if factors is None or factors.empty:
            return pd.DataFrame({
                "signal": float("nan"),
                "signal_strength": 0.0,
            }, index=data.index)

        # 归一化
        normalized = self._normalize(factors)

        # 加权打分
        score = pd.Series(0.0, index=data.index)
        for name, weight in self.weights.items():
            if name in normalized.columns:
                score += normalized[name] * weight

        # 转换为信号
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = float("nan")
        signals.loc[score > self.buy_threshold, "signal"] = 1
        signals.loc[score < self.sell_threshold, "signal"] = -1

        # 信号强度：归一化到 [0, 1]
        score_abs_max = score.abs().max() or 1.0
        signals["signal_strength"] = (score.abs() / score_abs_max).clip(0, 1)
        signals["score"] = score

        return signals

    def _compute_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """根据 weights 从注册中心计算所有需要的因子。"""
        factor_dfs = {}
        for name in self.weights:
            try:
                factor = FactorRegistry.create(name)
                result = factor.compute(data)
                if isinstance(result, pd.DataFrame):
                    for col in result.columns:
                        factor_dfs[f"{name}_{col}"] = result[col]
                else:
                    factor_dfs[name] = result
            except (KeyError, Exception):
                continue

        if not factor_dfs:
            return pd.DataFrame(index=data.index)

        return pd.DataFrame(factor_dfs, index=data.index)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """因子归一化。"""
        if self.normalize == "zscore":
            return ((df - df.mean()) / (df.std() + 1e-12)).fillna(0)
        elif self.normalize == "rank":
            return df.rank(pct=True).fillna(0.5) * 2 - 1
        elif self.normalize == "minmax":
            return ((df - df.min()) / (df.max() - df.min() + 1e-12) * 2 - 1).fillna(0)
        return df
