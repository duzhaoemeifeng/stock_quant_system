"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
报告生成器 — 将分析结果格式化为可读报告。
"""

from datetime import datetime

import pandas as pd


class ReportGenerator:
    """自动报告生成器。

    将市场分析、策略推荐、回测结果综合成结构化报告。

    使用方法:
        gen = ReportGenerator()
        report = gen.generate(market_regime, strategy_reco, backtest_result, opt_result)
    """

    @classmethod
    def generate(
        cls,
        symbol: str,
        data: pd.DataFrame,
        market_regime: dict,
        strategy_reco: dict,
        backtest_result: dict | None = None,
        opt_result: dict | None = None,
    ) -> str:
        """生成完整分析报告（Markdown格式）。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [
            f"# 📊 量化分析报告",
            "",
            f"**生成时间**: {now} | **股票代码**: {symbol}",
            f"**数据区间**: {data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}",
            f"**交易日数**: {len(data)}",
            "",
            "---",
            "",
            "## 🔍 市场状态诊断",
            "",
            market_regime.get("description", "分析不可用"),
            "",
            cls._regime_details(market_regime),
            "",
            "---",
            "",
            "## 🎯 策略推荐",
            "",
            f"- **推荐策略**: {strategy_reco.get('primary', 'N/A')}",
            f"- **信号类型**: {strategy_reco.get('signal_type', 'N/A')}",
            f"- **推荐理由**: {strategy_reco.get('reason', 'N/A')}",
            f"- **仓位模型**: {strategy_reco.get('position_model', 'N/A')}",
            f"- **止损设置**: {strategy_reco.get('stop_loss', 0):.0%}",
            f"- **建议仓位**: {strategy_reco.get('recommended_position', 0):.0%}",
            "",
        ]

        # 推荐参数
        params = strategy_reco.get("params", {})
        if params:
            lines.append("**推荐参数**:")
            for k, v in params.items():
                lines.append(f"  - `{k}` = {v}")
            lines.append("")

        lines.extend([
            "---",
            "",
        ])

        # 回测结果
        if backtest_result:
            lines.extend([
                "## 📈 回测绩效",
                "",
                cls._backtest_summary(backtest_result),
                "",
            ])

        # 优化结果
        if opt_result and opt_result.get("best_params"):
            lines.extend([
                "## 🔧 参数优化结果",
                "",
                f"- 测试组合数: {opt_result.get('n_tested', 0)}",
                f"- 最优参数: {opt_result.get('best_params', {})}",
                f"- 样本内夏普: {opt_result.get('best_sharpe_in', 0):.3f}",
                f"- 样本外夏普: {opt_result.get('best_sharpe_out', 0):.3f}",
                f"- 夏普衰减: {opt_result.get('sharpe_drop', 0):.3f}",
                "",
            ])

            if opt_result.get("is_overfitted"):
                lines.append("> ⚠️ **过拟合风险**: 样本外夏普显著低于样本内，策略可能过拟合。")
            else:
                lines.append("> ✅ **稳健性**: 样本内外夏普差异可接受，策略相对稳健。")

            lines.append("")
            lines.append("**参数敏感性（影响越大越需谨慎）:**")
            for param, sens in sorted(opt_result.get("sensitivity", {}).items(),
                                       key=lambda x: x[1], reverse=True):
                bar = "█" * min(int(sens * 50), 20)
                lines.append(f"  - `{param}`: {bar} ({sens:.3f})")

        lines.extend([
            "",
            "---",
            "",
            "## ⚠️ 风险提示",
            "",
            "1. 以上所有分析基于历史数据，不构成投资建议",
            "2. 量化模型存在过拟合风险，市场条件变化可能导致策略失效",
            "3. 实盘交易前请在模拟环境中充分验证",
            "4. 建议设置止损、控制单票仓位不超过总资产20%",
            "5. 投资有风险，入市须谨慎",
            "",
            "---",
            f"*报告由量化交易 Agent 自动生成 ({now})*",
        ])

        return "\n".join(lines)

    @staticmethod
    def _regime_details(regime: dict) -> str:
        rows = [
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 市场状态 | {regime.get('regime_label', '-')} | {regime.get('regime', '-')} |",
            f"| ADX | {regime.get('adx', 0):.1f} | {'有趋势(>25)' if regime.get('adx', 0) > 25 else '无趋势'} |",
            f"| RSI | {regime.get('rsi', 0):.1f} | {'超买' if regime.get('rsi', 0) > 70 else '超卖' if regime.get('rsi', 0) < 30 else '中性'} |",
            f"| 波动率 | {regime.get('volatility', 0):.1%} | {regime.get('volatility_label', '-')} |",
            f"| 风险等级 | {regime.get('risk_level', '-')} | 评分: {regime.get('risk_score', 0):.2f} |",
            f"| 建议仓位 | {regime.get('recommended_position', 0):.0%} | Agent自动计算 |",
        ]
        return "\n".join(rows)

    @staticmethod
    def _backtest_summary(result: dict) -> str:
        rows = [
            "| 指标 | 数值 | 评级 |",
            "|------|------|------|",
            f"| 累计收益率 | {result.get('total_return', 0):.2%} | {ReportGenerator._star(result.get('total_return', 0) * 100)} |",
            f"| 年化收益率 | {result.get('annual_return', 0):.2%} | {ReportGenerator._star(result.get('annual_return', 0) * 100)} |",
            f"| 夏普比率 | {result.get('sharpe_ratio', 0):.2f} | {'⭐' * min(5, max(1, int(result.get('sharpe_ratio', 0)) + 1))} |",
            f"| 最大回撤 | {result.get('max_drawdown', 0):.2%} | {'⚠️' if result.get('max_drawdown', 0) < -0.2 else '✓'} |",
            f"| 胜率 | {result.get('win_rate', 0):.1%} | {ReportGenerator._star(result.get('win_rate', 0) * 100)} |",
            f"| 交易次数 | {result.get('trade_count', 0)} | - |",
        ]
        return "\n".join(rows)

    @staticmethod
    def _star(val: float) -> str:
        if val > 20:
            return "⭐⭐⭐⭐⭐"
        elif val > 10:
            return "⭐⭐⭐⭐"
        elif val > 5:
            return "⭐⭐⭐"
        elif val > 0:
            return "⭐⭐"
        else:
            return "⭐"
