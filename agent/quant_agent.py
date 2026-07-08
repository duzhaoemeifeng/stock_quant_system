"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
量化交易 Agent — 统一入口，协调所有子Agent。

功能:
    1. 自动市场状态诊断
    2. 策略自动选择与推荐
    3. 参数自动优化
    4. 综合报告生成

使用方法:
    agent = QuantAgent()
    result = agent.analyze(data, symbol="000001")
"""

import numpy as np
import pandas as pd

from .market_regime import MarketRegimeDetector
from .strategy_selector import StrategySelector
from .auto_optimizer import AutoOptimizer
from .report_generator import ReportGenerator


class QuantAgent:
    """量化交易 Agent。

    自动完成市场分析 → 策略推荐 → 参数优化 → 报告生成全流程。

    使用方法:
        agent = QuantAgent()
        result = agent.analyze(data, symbol="000001")
        print(result["report"])  # 完整分析报告
        print(result["recommendation"])  # 策略推荐
    """

    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.optimizer = AutoOptimizer()

    def analyze(
        self,
        data: pd.DataFrame,
        symbol: str = "000001",
        backtest_fn=None,
    ) -> dict:
        """执行完整 Agent 分析流程。

        Args:
            data: OHLCV 数据（统一Schema）。
            symbol: 股票代码。
            backtest_fn: 可选的回测函数 fn(data, signals) -> result_dict。

        Returns:
            dict 包含:
                - market_regime: 市场状态
                - recommendation: 策略推荐
                - optimization: 参数优化结果
                - report: Markdown 报告
                - backtest: 回测结果（如果提供了 backtest_fn）
        """
        # 步骤1: 市场状态诊断
        market_regime = self.regime_detector.detect(data)

        # 步骤2: 策略自动推荐
        recommendation = StrategySelector.recommend(market_regime)

        # 步骤3: 参数优化（如果策略有参数配置）
        optimization = None
        strategy_params = recommendation.get("params", {})
        if strategy_params:
            param_grid = self._build_param_grid(recommendation)
            if param_grid:
                def strategy_fn(d, p):
                    return self._generate_default_signals(d, recommendation["signal_type"], p)

                optimization = self.optimizer.optimize(data, strategy_fn, param_grid)

        # 步骤4: 回测（默认策略+最优参数）
        backtest_result = None
        if backtest_fn and data is not None:
            try:
                best_params = optimization["best_params"] if optimization and optimization.get("best_params") else strategy_params
                signals = self._generate_default_signals(data, recommendation["signal_type"], best_params)
                backtest_result = backtest_fn(data, signals)
            except Exception:
                pass

        # 步骤5: 生成报告
        report = ReportGenerator.generate(
            symbol=symbol,
            data=data,
            market_regime=market_regime,
            strategy_reco=recommendation,
            backtest_result=backtest_result,
            opt_result=optimization,
        )

        return {
            "symbol": symbol,
            "market_regime": market_regime,
            "recommendation": recommendation,
            "optimization": optimization,
            "backtest": backtest_result,
            "report": report,
        }

    def quick_scan(self, data: pd.DataFrame) -> dict:
        """快速扫描：仅做市场诊断+策略推荐。"""
        regime = self.regime_detector.detect(data)
        reco = StrategySelector.recommend(regime)
        return {
            "market_regime": regime,
            "recommendation": reco,
            "summary": f"{regime['regime_label']} → 推荐 {reco['primary']} ({reco['reason']})",
        }

    def _generate_default_signals(
        self,
        data: pd.DataFrame,
        signal_type: str,
        params: dict,
    ) -> pd.DataFrame:
        """根据信号类型和参数生成默认信号。"""
        close = data["close"].astype(float)

        if signal_type == "trend":
            fast = params.get("fast_window", 5)
            slow = params.get("slow_window", 20)
            fast_ma = close.rolling(window=fast, min_periods=fast).mean()
            slow_ma = close.rolling(window=slow, min_periods=slow).mean()

            signals = pd.DataFrame(index=data.index)
            signals["position"] = 0
            signals.loc[fast_ma > slow_ma, "position"] = 1
            signals.loc[fast_ma < slow_ma, "position"] = -1
            signals["signal"] = signals["position"].diff()
            signals.loc[signals["signal"] == 0, "signal"] = np.nan

        elif signal_type == "reversal":
            window = params.get("window", 14)
            oversold = params.get("oversold", 30)
            overbought = params.get("overbought", 70)

            delta = close.diff()
            gain = delta.clip(lower=0).ewm(alpha=1/window, adjust=False).mean()
            loss = (-delta).clip(lower=0).ewm(alpha=1/window, adjust=False).mean()
            rsi = 100 - 100 / (1 + gain / (loss + 1e-12))

            signals = pd.DataFrame(index=data.index)
            signals["signal"] = np.nan
            exit_oversold = (rsi.shift(1) < oversold) & (rsi >= oversold)
            exit_overbought = (rsi.shift(1) > overbought) & (rsi <= overbought)
            signals.loc[exit_oversold, "signal"] = 1
            signals.loc[exit_overbought, "signal"] = -1

        else:
            signals = pd.DataFrame({"signal": np.nan}, index=data.index)

        return signals

    def _build_param_grid(self, recommendation: dict) -> dict | None:
        """根据策略类型构建参数搜索网格。"""
        signal_type = recommendation.get("signal_type", "")

        if signal_type == "trend":
            return {
                "fast_window": [3, 5, 10, 15],
                "slow_window": [20, 30, 40, 60],
            }
        elif signal_type == "reversal":
            return {
                "window": [7, 14, 21],
                "oversold": [20, 30, 40],
                "overbought": [60, 70, 80],
            }
        return None
