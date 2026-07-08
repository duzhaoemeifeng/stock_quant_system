"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
策略自动选择 Agent — 根据市场状态推荐最优策略。
"""

import pandas as pd


class StrategySelector:
    """策略自动选择器。

    基于市场状态（趋势/震荡）和波动率，自动推荐最适合的策略组合。

    使用方法:
        selector = StrategySelector()
        recommendation = selector.recommend(regime_info)
    """

    # 策略知识库
    STRATEGY_KB = {
        "trending_up": {
            "primary": "双均线趋势跟踪",
            "params": {"fast_window": 5, "slow_window": 20},
            "signal_type": "trend",
            "reason": "上升趋势中趋势策略表现最佳，短周期捕捉快涨机会",
            "position_model": "fixed",
            "stop_loss": 0.05,
        },
        "trending_down": {
            "primary": "空仓观望/逆势反转",
            "params": {"window": 14, "oversold": 20, "overbought": 60},
            "signal_type": "reversal",
            "reason": "下跌趋势建议观望或使用超跌反弹策略，严格止损",
            "position_model": "fixed",
            "stop_loss": 0.03,
        },
        "ranging": {
            "primary": "RSI均值回归",
            "params": {"window": 14, "oversold": 30, "overbought": 70},
            "signal_type": "reversal",
            "reason": "震荡市场适合均值回归，在超卖买入、超买卖出",
            "position_model": "atr",
            "stop_loss": 0.05,
        },
        "transitional": {
            "primary": "多因子打分",
            "params": {"weights": {"RSIFactor": 0.3, "RateOfChangeFactor": 0.3, "ATRFactor": 0.4}},
            "signal_type": "multi_factor",
            "reason": "方向不明时采用多因子打分，降低单因子依赖",
            "position_model": "kelly",
            "stop_loss": 0.05,
        },
    }

    @classmethod
    def recommend(cls, regime_info: dict) -> dict:
        """根据市场状态推荐策略。

        Args:
            regime_info: MarketRegimeDetector.detect() 的输出。

        Returns:
            dict 包含: 推荐策略、参数、理由、仓位模型、止损设置
        """
        regime = regime_info.get("regime", "transitional")
        vol_level = regime_info.get("volatility_level", "medium")

        base_reco = cls.STRATEGY_KB.get(regime, cls.STRATEGY_KB["transitional"]).copy()

        # 根据波动率微调
        if vol_level == "high":
            base_reco["stop_loss"] = max(0.03, base_reco["stop_loss"] * 0.7)
            base_reco["reason"] += "；高波动环境建议缩小止损幅度"
            if base_reco["signal_type"] == "trend":
                base_reco["params"]["fast_window"] = min(base_reco["params"].get("fast_window", 5), 3)
                base_reco["params"]["slow_window"] = base_reco["params"].get("slow_window", 20)
        elif vol_level == "low":
            base_reco["position_model"] = "fixed"
            base_reco["reason"] += "；低波动环境可适当提高仓位"

        base_reco["recommended_position"] = regime_info.get("recommended_position", 0.15)

        return base_reco

    @classmethod
    def list_all_strategies(cls) -> dict:
        """列出所有策略及适用场景。"""
        return {
            "双均线趋势跟踪": {
                "适用": "上升/下降趋势",
                "信号类型": "趋势",
                "特点": "顺势而为，趋势行情收益高，震荡市频繁磨损"
            },
            "MACD金叉死叉": {
                "适用": "中等趋势",
                "信号类型": "趋势",
                "特点": "比双均线少一些假信号，但信号延迟更大"
            },
            "RSI均值回归": {
                "适用": "震荡盘整",
                "信号类型": "反转",
                "特点": "超卖买入超买卖出，趋势市可能接飞刀"
            },
            "布林带回归": {
                "适用": "低波动震荡",
                "信号类型": "反转",
                "特点": "触及上下轨后回归，需配合波动率过滤"
            },
            "多因子打分": {
                "适用": "方向不明/复杂市场",
                "信号类型": "多因子",
                "特点": "综合多维度信号，降低单因子偏差，但权重需调优"
            },
        }
