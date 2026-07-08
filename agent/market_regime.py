"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
市场状态识别 Agent — 自动判断当前处于趋势/震荡/高波动/低波动状态。
"""

import numpy as np
import pandas as pd


class MarketRegimeDetector:
    """市场状态识别器。

    分析价格走势，自动判断：
    - 趋势方向（上升/下降/震荡）
    - 波动率状态（高/中/低）
    - 市场强度评分

    使用方法:
        detector = MarketRegimeDetector()
        regime = detector.detect(data)  # 返回市场状态字典
    """

    def __init__(self, trend_window: int = 60, vol_window: int = 20):
        self.trend_window = trend_window
        self.vol_window = vol_window

    def detect(self, data: pd.DataFrame) -> dict:
        """识别当前市场状态。

        Returns:
            dict 包含:
                - regime: 市场状态标签
                - trend_strength: 趋势强度 (0-1)
                - volatility_level: 波动率等级
                - recommended_position: 建议仓位比例
                - risk_level: 风险等级
                - description: 中文描述
        """
        close = data["close"].astype(float)
        n = len(close)

        # 1. 趋势分析
        sma_short = close.rolling(20).mean()
        sma_long = close.rolling(self.trend_window).mean()
        current_price = close.iloc[-1]
        trend_slope = (sma_long.iloc[-1] / sma_long.iloc[-min(60, n)] - 1) if n >= 60 else 0

        # 价格相对均线位置
        if current_price > sma_short.iloc[-1] * 1.03:
            trend_direction = "strong_up"
        elif current_price > sma_short.iloc[-1]:
            trend_direction = "up"
        elif current_price < sma_short.iloc[-1] * 0.97:
            trend_direction = "strong_down"
        elif current_price < sma_short.iloc[-1]:
            trend_direction = "down"
        else:
            trend_direction = "sideways"

        # 2. 波动率分析
        log_ret = np.log(close / close.shift(1))
        current_vol = log_ret.iloc[-self.vol_window:].std() * np.sqrt(252)

        # 历史波动率分位
        rolling_vol = log_ret.rolling(self.vol_window).std() * np.sqrt(252)
        vol_percentile = (rolling_vol.iloc[-1:].iloc[0] < rolling_vol.dropna()).mean() if len(rolling_vol.dropna()) > 0 else 0.5

        if vol_percentile > 0.8:
            vol_level = "high"
            vol_label = "高波动"
        elif vol_percentile > 0.5:
            vol_level = "medium"
            vol_label = "中等波动"
        else:
            vol_level = "low"
            vol_label = "低波动"

        # 3. RSI
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta).clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / (loss + 1e-12)
        rsi = 100 - 100 / (1 + rs)
        current_rsi = rsi.iloc[-1]

        # 4. 趋势强度 (ADX简化)
        tr_high_low = data["high"] - data["low"]
        tr_high_close = (data["high"] - close.shift(1)).abs()
        tr_low_close = (data["low"] - close.shift(1)).abs()
        tr = pd.concat([tr_high_low, tr_high_close, tr_low_close], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/14, adjust=False).mean()
        plus_dm = np.where((data["high"].diff() > data["low"].diff().abs()) &
                            (data["high"].diff() > 0), data["high"].diff(), 0)
        minus_dm = np.where((data["low"].diff().abs() > data["high"].diff()) &
                             (data["low"].diff() < 0), -data["low"].diff(), 0)
        plus_di = pd.Series(plus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / (atr + 1e-12) * 100
        minus_di = pd.Series(minus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / (atr + 1e-12) * 100
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-12) * 100)
        adx = dx.ewm(alpha=1/14, adjust=False).mean()
        current_adx = adx.iloc[-1]

        # 5. 综合判断
        if current_adx > 25 and trend_slope > 0.03:
            regime = "trending_up"
            regime_label = "上升趋势"
            recommended_position = min(0.8, 0.3 + current_adx / 200)
        elif current_adx > 25 and trend_slope < -0.03:
            regime = "trending_down"
            regime_label = "下降趋势"
            recommended_position = 0.1
        elif current_adx < 20:
            regime = "ranging"
            regime_label = "震荡盘整"
            recommended_position = 0.15
        else:
            regime = "transitional"
            regime_label = "方向不明"
            recommended_position = 0.1

        # 波动率调整仓位
        if vol_level == "high":
            recommended_position *= 0.5

        # 风险等级
        if vol_level == "high" and current_adx > 25:
            risk = "高"
            risk_score = 0.8
        elif vol_level == "high" or (current_adx > 25 and regime == "trending_down"):
            risk = "中高"
            risk_score = 0.6
        elif vol_level == "low" and regime == "trending_up":
            risk = "低"
            risk_score = 0.2
        else:
            risk = "中"
            risk_score = 0.4

        # 生成描述
        description = (
            f"当前市场处于 **{regime_label}** 状态，"
            f"波动率为 **{vol_label}**（分位{vol_percentile:.0%}），"
            f"ADX={current_adx:.1f}（{'有趋势' if current_adx > 25 else '无趋势'}），"
            f"RSI={current_rsi:.1f}，"
            f"建议仓位 **{recommended_position:.0%}**，"
            f"风险等级: **{risk}**。"
        )

        return {
            "regime": regime,
            "regime_label": regime_label,
            "trend_direction": trend_direction,
            "trend_slope": trend_slope,
            "volatility_level": vol_level,
            "volatility_label": vol_label,
            "vol_percentile": vol_percentile,
            "adx": current_adx,
            "rsi": current_rsi,
            "volatility": current_vol,
            "recommended_position": recommended_position,
            "risk_level": risk,
            "risk_score": risk_score,
            "description": description,
        }
