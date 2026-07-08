"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。对话回复均为程序自动生成，
 基于历史统计规律，不具备预测能力。
==================================================
对话式量化 Agent — 支持自然语言交互。

支持中文自然语言查询，包括：
- 股票分析、市场诊断、策略推荐
- 概念解释、策略对比、风险提示
- 参数优化、数据查询、帮助指令

使用方法:
    chat = ChatAgent()
    reply = chat.respond("帮我分析一下000001")
"""

import re
from datetime import datetime

import numpy as np
import pandas as pd

from .market_regime import MarketRegimeDetector
from .strategy_selector import StrategySelector


class ChatAgent:
    """对话式量化交易 Agent。

    基于规则引擎 + 关键词匹配实现自然语言理解，
    无需 LLM API，完全本地运行。

    使用方法:
        chat = ChatAgent()
        chat.load_data("000001", data)  # 加载数据
        reply = chat.respond("现在是什么市场状态？")
    """

    def __init__(self):
        self.symbol = "000001"
        self.symbol_name = ""
        self.data: pd.DataFrame | None = None
        self.regime: dict | None = None
        self.recommendation: dict | None = None
        self.conversation_history: list[dict] = []

        self.detector = MarketRegimeDetector()

        # 股票代码→名称映射
        self._stock_names = {
            "000001": "平安银行", "000002": "万科A", "000858": "五粮液",
            "002415": "海康威视", "300750": "宁德时代", "600036": "招商银行",
            "600276": "恒瑞医药", "600519": "贵州茅台", "600887": "伊利股份",
            "601318": "中国平安", "000651": "格力电器", "002594": "比亚迪",
            "601166": "兴业银行", "600030": "中信证券", "000333": "美的集团",
            "688981": "中芯国际", "601899": "紫金矿业", "002475": "立讯精密",
        }

        # 知识库
        self._knowledge = self._build_knowledge()

    def load_data(self, symbol: str, data: pd.DataFrame, name: str = ""):
        """加载股票数据并自动分析。"""
        self.symbol = symbol
        self.symbol_name = name or self._stock_names.get(symbol, symbol)
        self.data = data

        # 自动分析
        try:
            self.regime = self.detector.detect(data)
            self.recommendation = StrategySelector.recommend(self.regime)
        except Exception:
            self.regime = None
            self.recommendation = None

    def respond(self, user_input: str) -> str:
        """处理用户输入并返回回复。

        Args:
            user_input: 用户自然语言输入。

        Returns:
            Agent 回复文本（Markdown 格式）。
        """
        text = user_input.strip()

        # 保存对话历史
        self.conversation_history.append({"role": "user", "content": text})

        # 意图识别
        intent, params = self._parse_intent(text)

        # 路由到处理函数
        handler = self._get_handler(intent)
        reply = handler(params, text)

        self.conversation_history.append({"role": "agent", "content": reply})
        return reply

    # ============================================================
    # 意图识别
    # ============================================================

    def _parse_intent(self, text: str) -> tuple[str, dict]:
        """解析用户意图和参数。"""
        params = {}

        # 提取股票代码
        code_match = re.search(r'(\d{6})', text)
        if code_match:
            params["symbol"] = code_match.group(1)

        # 提取股票名称
        for code, name in self._stock_names.items():
            if name in text:
                params["symbol"] = code
                break

        # 意图匹配（优先级从高到低）
        intents = [
            (["分析", "看看", "查", "看一下", "帮我分析", "走势", "怎么看", "怎么样$",
              "帮我看看", "分析一下", "表现如何"], "analyze"),
            (["市场", "行情", "状态", "大势", "盘面", "环境", "趋势判断"], "market"),
            (["推荐", "建议", "选什么", "用什么策略", "哪种", "哪个好", "最优"], "recommend"),
            (["对比", "区别", "比较", "哪个更好", "优缺点"], "compare"),
            (["什么是", "解释", "说明一下", "什么意思", "定义", "怎么算"], "explain"),
            (["参数", "优化", "调参", "最优参数", "网格搜索"], "optimize"),
            (["风险", "止损", "风控", "仓位", "安全"], "risk"),
            (["回测", "绩效", "收益", "夏普", "回撤", "胜率"], "backtest"),
            (["你好", "嗨", "hello", "hi", "在吗"], "greet"),
            (["帮助", "help", "能做什么", "功能", "怎么用"], "help"),
        ]

        for patterns, intent in intents:
            for pat in patterns:
                if pat in text or (pat.endswith("$") and text.rstrip("?？。") == pat[:-1]):
                    return intent, params

        return "chat", params

    def _get_handler(self, intent: str):
        """获取意图对应的处理函数。"""
        return getattr(self, f"_handle_{intent}", self._handle_chat)

    # ============================================================
    # 意图处理函数
    # ============================================================

    def _handle_analyze(self, params: dict, text: str) -> str:
        """处理分析请求。"""
        symbol = params.get("symbol", self.symbol)
        name = self._stock_names.get(symbol, symbol)

        if symbol == self.symbol and self.regime:
            regime = self.regime
            reco = self.recommendation
        else:
            reply = f"我需要先加载 **{name}({symbol})** 的数据才能分析。\n\n"
            reply += f"请在侧边栏输入 `{symbol}` 并点击「开始回测」或「启动 Agent 分析」，然后我就能帮你深入分析了。\n\n"
            reply += f"目前我手上有 **{self.symbol_name}({self.symbol})** 的数据，需要我先分析它吗？"
            return reply

        close = self.data["close"]
        current = close.iloc[-1]
        change_20d = (close.iloc[-1] / close.iloc[-min(21, len(close))] - 1) if len(close) >= 21 else 0
        ma20 = close.rolling(20).mean().iloc[-1]

        lines = [
            f"## 📊 {name}({symbol}) 分析报告",
            "",
            f"**最新价**: {current:.2f} 元 | **20日涨跌**: {change_20d:+.2%}",
            f"**MA20**: {ma20:.2f} | {'高于均线 📈' if current > ma20 else '低于均线 📉'}",
            "",
            f"### 市场状态: {regime['regime_label']}",
            f"{regime['description']}",
            "",
            f"### 🎯 当前推荐: {self.recommendation.get('primary', 'N/A')}",
            f"> {self.recommendation.get('reason', '')}",
            "",
            f"### 关键指标",
            f"| 指标 | 数值 | 解读 |",
            f"|------|------|------|",
            f"| ADX | {regime['adx']:.1f} | {'趋势明确' if regime['adx'] > 25 else '方向不明确'} |",
            f"| RSI(14) | {regime['rsi']:.1f} | {'超买区' if regime['rsi'] > 70 else '超卖区' if regime['rsi'] < 30 else '中性区'} |",
            f"| 波动率 | {regime['volatility']:.1%} | {regime['volatility_label']} |",
            f"| 风险等级 | {regime['risk_level']} | - |",
            f"| 建议仓位 | {regime['recommended_position']:.0%} | Agent自动评估 |",
            "",
            f"### 💡 操作建议",
            f"- 止损设置: **{self.recommendation.get('stop_loss', 0.05):.0%}**",
            f"- 仓位模型: **{self.recommendation.get('position_model', 'fixed')}**",
            f"- 推荐参数: `{self.recommendation.get('params', {})}`",
            "",
            "> ⚠️ 以上为 Agent 基于历史数据的分析，不构成交易建议。",
        ]
        return "\n".join(lines)

    def _handle_market(self, params: dict, text: str) -> str:
        """处理市场状态查询。"""
        if not self.regime:
            return "请先加载数据，我才能分析市场状态。可以输入「分析 + 股票代码」开始。比如：「分析一下000001」"

        r = self.regime
        lines = [
            f"## 🔍 当前市场状态（{self.symbol_name}）",
            "",
            f"**{r['regime_label']}** | 波动率: {r['volatility_label']} | 风险: {r['risk_level']}",
            "",
            f"**趋势强度 (ADX)**: {r['adx']:.1f} — {'趋势比较明确，适合趋势跟踪策略' if r['adx'] > 25 else '趋势不明显，建议使用震荡策略或观望'}",
            f"**RSI(14)**: {r['rsi']:.1f} — {'高位，注意回调风险' if r['rsi'] > 70 else '低位，可能存在反弹机会' if r['rsi'] < 30 else '中性区间，无极端信号'}",
            f"**年化波动率**: {r['volatility']:.1%} — {'波动较高，建议缩小仓位' if r['volatility'] > 0.4 else '波动适中' if r['volatility'] > 0.2 else '波动较低，可适当提高仓位'}",
            "",
            f"**Agent 建议仓位**: {r['recommended_position']:.0%}",
            "",
            "> 市场状态每时每刻都在变化，建议定期重新评估。",
        ]
        return "\n".join(lines)

    def _handle_recommend(self, params: dict, text: str) -> str:
        """处理策略推荐。"""
        if not self.recommendation:
            return "我需要先分析数据才能推荐策略。请先输入「分析 + 股票代码」。"

        reco = self.recommendation
        lines = [
            f"## 🎯 策略推荐（基于 {self.symbol_name} 当前市场状态）",
            "",
            f"### 首选: {reco['primary']}",
            f"> {reco['reason']}",
            "",
            f"| 配置项 | 推荐值 |",
            f"|--------|--------|",
            f"| 仓位模型 | {reco.get('position_model', 'fixed')} |",
            f"| 止损比例 | {reco.get('stop_loss', 0.05):.0%} |",
            f"| 建议仓位 | {reco.get('recommended_position', 0.15):.0%} |",
            "",
            "### 📚 所有策略速览",
        ]
        for name, info in StrategySelector.list_all_strategies().items():
            marker = "👉 " if name == reco["primary"] else "- "
            lines.append(f"{marker}**{name}**: {info['特点']}（适用: {info['适用']}）")

        lines.append("\n> 需要我详细对比某两个策略吗？试试输入「对比双均线和MACD」")
        return "\n".join(lines)

    def _handle_compare(self, params: dict, text: str) -> str:
        """处理策略对比。"""
        knowledge = self._knowledge["strategies"]

        found = []
        for key, info in knowledge.items():
            if any(kw in text for kw in info["keywords"]):
                found.append((key, info))

        if len(found) < 2:
            return ("我可以帮你对比以下策略：\n\n"
                    "- **双均线 vs MACD**: 都是趋势策略，MACD信号更少但更可靠\n"
                    "- **趋势 vs 均值回归**: 适用不同市场状态，互补使用\n"
                    "- **固定仓位 vs ATR动态**: 静态 vs 动态风险敞口\n\n"
                    "你想对比哪两个？比如：「对比双均线和RSI」")

        lines = ["## ⚖️ 策略对比", ""]
        lines.append("| 维度 | " + " | ".join(name for name, _ in found) + " |")
        lines.append("|------|" + "|".join("------" for _ in found) + "|")

        dimensions = ["适用市场", "信号类型", "假信号风险", "延迟"]
        for dim in dimensions:
            vals = []
            for _, info in found:
                vals.append(info.get(dim, "-"))
            lines.append(f"| {dim} | " + " | ".join(vals) + " |")

        lines.append("")
        lines.append("**建议**: 震荡市用均值回归，趋势市用趋势跟踪，两者混合可以降低单策略失效风险。")
        return "\n".join(lines)

    def _handle_explain(self, params: dict, text: str) -> str:
        """处理概念解释。"""
        knowledge = self._knowledge["concepts"]
        for key, info in knowledge.items():
            if any(kw in text for kw in info["keywords"]):
                return f"## 📖 {info['name']}\n\n{info['explanation']}"

        return (
            "我可以解释以下概念：\n\n"
            "- 📊 **夏普比率** — 衡量风险调整后收益\n"
            "- 📉 **最大回撤** — 最大的累计亏损幅度\n"
            "- 📈 **MACD** — 趋势跟踪指标\n"
            "- 🔄 **RSI** — 超买超卖指标\n"
            "- 📐 **ADX** — 趋势强度指标\n"
            "- 🎯 **凯利公式** — 最优仓位公式\n"
            "- 🛡️ **卡玛比率** — 年化收益/最大回撤\n\n"
            "你想了解哪个？比如：「解释一下夏普比率」"
        )

    def _handle_optimize(self, params: dict, text: str) -> str:
        """处理参数优化请求。"""
        if self.data is None:
            return "请先加载数据。输入「分析 + 股票代码」开始。"

        return (
            "## 🔧 参数优化\n\n"
            "我支持对策略参数进行**网格搜索优化**：\n\n"
            "1. 切换到「📊 手动回测」标签，选择策略和参数\n"
            "2. 或使用「🤖 AI Agent 智能分析」标签，自动优化\n\n"
            "Agent 会自动：\n"
            "- 穷举参数组合\n"
            "- 样本内/外分割验证\n"
            "- 检测过拟合风险\n"
            "- 输出 Top 5 最优参数\n\n"
            "> 已在「AI Agent 智能分析」标签页启动优化，点击即可查看结果。"
        )

    def _handle_risk(self, params: dict, text: str) -> str:
        """处理风控查询。"""
        return (
            "## 🛡️ 风控系统\n\n"
            "本系统内置 **5道风控防线**：\n\n"
            "| 防线 | 机制 | 默认参数 |\n"
            "|------|------|----------|\n"
            "| 1. 固定止损 | 单笔亏损到达阈值即平仓 | 7% |\n"
            "| 2. 移动止损 | 从最高价回撤超阈值即平仓 | 15% |\n"
            "| 3. 日内限制 | 当日亏损超阈值停止交易 | 3% |\n"
            "| 4. 总回撤限制 | 账户从峰值回撤超阈值全部平仓 | 25% |\n"
            "| 5. 连续亏损 | 连续亏损N次暂停交易 | 5次 |\n\n"
            "**风控建议**:\n"
            "- 单票仓位不超过总资产 **20%**\n"
            "- 总仓位不超过 **80%**，永远留现金\n"
            "- 止损设定根据波动率动态调整\n"
            "- 不要在亏损时加仓（不接飞刀）\n\n"
            f"当前 **{self.symbol_name}** 风险等级: **{self.regime['risk_level'] if self.regime else '未知'}**"
        )

    def _handle_backtest(self, params: dict, text: str) -> str:
        """处理回测结果查询。"""
        if self.data is None:
            return "请先运行回测。切换到「📊 手动回测」标签页，点击「开始回测」。"

        close = self.data["close"]
        total_ret = (close.iloc[-1] / close.iloc[0] - 1)
        n_days = len(close)
        ann_ret = (1 + total_ret) ** (252 / n_days) - 1

        rets = close.pct_change().dropna()
        sharpe = (rets.mean() * 252 - 0.03) / (rets.std() * np.sqrt(252)) if rets.std() > 0 else 0

        peak = close.expanding().max()
        max_dd = ((close - peak) / peak).min()

        return (
            f"## 📈 {self.symbol_name} 基础统计\n\n"
            f"| 指标 | 数值 |\n"
            f"|------|------|\n"
            f"| 数据区间 | {self.data.index[0].strftime('%Y-%m-%d')} ~ {self.data.index[-1].strftime('%Y-%m-%d')} |\n"
            f"| 交易日数 | {n_days} |\n"
            f"| 累计收益 | {total_ret:.2%} |\n"
            f"| 年化收益 | {ann_ret:.2%} |\n"
            f"| 年化波动率 | {rets.std() * np.sqrt(252):.2%} |\n"
            f"| 夏普比率 | {sharpe:.2f} |\n"
            f"| 最大回撤 | {max_dd:.2%} |\n"
            f"| 当前价 | {close.iloc[-1]:.2f} |\n\n"
            "> 💡 这只是基础统计，完整回测请切换到「📊 手动回测」标签页。"
        )

    def _handle_greet(self, params: dict, text: str) -> str:
        """处理问候。"""
        name = self.symbol_name or "朋友"
        return (
            f"你好！👋 我是量化交易 Agent，当前正在分析 **{name}**。\n\n"
            "你可以这样跟我对话：\n"
            "- 「分析一下这只股票」— 查看完整分析报告\n"
            "- 「现在市场怎么样」— 市场状态诊断\n"
            "- 「推荐什么策略」— 获取策略建议\n"
            "- 「什么是夏普比率」— 解释量化概念\n"
            "- 「对比双均线和MACD」— 策略对比\n"
            "- 「怎么控制风险」— 风控建议\n\n"
            "有什么我可以帮你的？"
        )

    def _handle_help(self, params: dict, text: str) -> str:
        """处理帮助请求。"""
        return (
            "## 🤖 对话式量化 Agent 使用指南\n\n"
            "### 你可以对我说：\n\n"
            "| 意图 | 示例 |\n"
            "|------|------|\n"
            "| 📊 股票分析 | 「分析一下000001」「帮我看看茅台」 |\n"
            "| 🔍 市场诊断 | 「现在市场怎么样」「大盘什么状态」 |\n"
            "| 🎯 策略推荐 | 「推荐什么策略」「哪种策略比较好」 |\n"
            "| ⚖️ 策略对比 | 「对比双均线和MACD」「趋势和震荡策略谁好」 |\n"
            "| 📖 概念解释 | 「什么是夏普比率」「MACD怎么用」 |\n"
            "| 🔧 参数优化 | 「帮我优化参数」「调参建议」 |\n"
            "| 🛡️ 风险控制 | 「怎么设置止损」「风控建议」 |\n"
            "| 📈 回测统计 | 「收益怎么样」「最大回撤多少」 |\n\n"
            "### 已加载\n"
            f"- 股票: **{self.symbol_name}** ({self.symbol})\n"
            f"- 数据: {len(self.data)} 个交易日（如果已加载）\n\n"
            "直接输入问题开始对话吧！"
        )

    def _handle_chat(self, params: dict, text: str) -> str:
        """处理一般闲聊。"""
        if "吗" in text or "？" in text or "?" in text:
            return (
                f"我理解你想了解更多关于 **{self.symbol_name}** 的信息。\n\n"
                f"你可以试试问我：\n"
                f"- 「**分析一下{self.symbol}**」— 查看详细分析\n"
                f"- 「**推荐策略**」— 获取策略建议\n"
                f"- 「**现在市场怎么样**」— 了解市场状态\n"
                f"- 「**帮助**」— 查看所有功能"
            )
        return (
            "我专注于量化交易分析，可以帮你：\n\n"
            "- 📊 分析股票走势\n"
            "- 🔍 诊断市场状态\n"
            "- 🎯 推荐交易策略\n"
            "- 📖 解释量化概念\n\n"
            "输入「**帮助**」查看完整功能列表，或者直接问问题！"
        )

    # ============================================================
    # 知识库
    # ============================================================

    def _build_knowledge(self) -> dict:
        """构建本地知识库。"""
        return {
            "strategies": {
                "双均线": {
                    "keywords": ["双均线", "均线", "MA", "SMA"],
                    "适用市场": "趋势明显",
                    "信号类型": "趋势跟踪",
                    "假信号风险": "震荡市高",
                    "延迟": "中等",
                },
                "MACD": {
                    "keywords": ["MACD", "指数平滑"],
                    "适用市场": "中等趋势",
                    "信号类型": "趋势跟踪",
                    "假信号风险": "中低",
                    "延迟": "较高",
                },
                "RSI": {
                    "keywords": ["RSI", "相对强弱", "超买超卖"],
                    "适用市场": "震荡盘整",
                    "信号类型": "均值回归",
                    "假信号风险": "趋势市高",
                    "延迟": "低",
                },
                "布林带": {
                    "keywords": ["布林", "BOLL", "bollinger"],
                    "适用市场": "低波动震荡",
                    "信号类型": "均值回归",
                    "假信号风险": "趋势市高",
                    "延迟": "低",
                },
            },
            "concepts": {
                "sharpe": {
                    "name": "夏普比率 (Sharpe Ratio)",
                    "keywords": ["夏普", "sharpe"],
                    "explanation": (
                        "**夏普比率 = (年化收益率 - 无风险利率) / 年化波动率**\n\n"
                        "衡量**每承担一单位风险能获得多少超额收益**。\n\n"
                        "- > 2.0 : 优秀\n"
                        "- 1.0 ~ 2.0 : 良好\n"
                        "- 0.5 ~ 1.0 : 一般\n"
                        "- < 0.5 : 较差\n"
                        "- < 0 : 亏钱策略\n\n"
                        "**注意**: 夏普假设收益率正态分布，极端行情下会失真。"
                    ),
                },
                "max_dd": {
                    "name": "最大回撤 (Max Drawdown)",
                    "keywords": ["回撤", "最大回撤", "drawdown"],
                    "explanation": (
                        "**最大回撤 = (净值最低点 - 净值最高点) / 净值最高点**\n\n"
                        "衡量策略**从最高点到最低点的最大累计亏损幅度**。\n\n"
                        "- < 10% : 低风险\n"
                        "- 10%~20% : 中等风险\n"
                        "- 20%~30% : 高风险\n"
                        "- > 30% : 极高风险，需重新审视策略\n\n"
                        "**你心理上能承受多大回撤？这是选择策略的关键。**"
                    ),
                },
                "macd": {
                    "name": "MACD 指标",
                    "keywords": ["MACD", "指数平滑异同"],
                    "explanation": (
                        "**MACD = 快线EMA(12) - 慢线EMA(26)**\n"
                        "**信号线 = MACD的EMA(9)**\n\n"
                        "- **金叉买入**: MACD上穿信号线\n"
                        "- **死叉卖出**: MACD下穿信号线\n"
                        "- **背离**: 价格新高但MACD不跟进 → 趋势衰竭\n\n"
                        "MACD信号比双均线少，假信号更少，但延迟更大。适合中等趋势行情。"
                    ),
                },
                "rsi": {
                    "name": "RSI 相对强弱指标",
                    "keywords": ["RSI", "相对强弱"],
                    "explanation": (
                        "**RSI = 100 - 100/(1 + 平均涨幅/平均跌幅)**\n\n"
                        "- **> 70**: 超买，可能回调 → 卖出信号\n"
                        "- **< 30**: 超卖，可能反弹 → 买入信号\n"
                        "- **50附近**: 中性，无明确方向\n\n"
                        "RSI在**震荡市**表现好，在**强趋势市**容易失灵（指标钝化）。"
                    ),
                },
                "kelly": {
                    "name": "凯利公式 (Kelly Criterion)",
                    "keywords": ["凯利", "kelly", "最优仓位"],
                    "explanation": (
                        "**f* = p - (1-p) / b**\n\n"
                        "- p = 胜率\n"
                        "- b = 盈亏比（平均盈利/平均亏损）\n\n"
                        "凯利公式计算**理论上最优的仓位比例**。\n\n"
                        "⚠️ **实际使用建议用1/4或1/2凯利**，因为：\n"
                        "- 历史胜率和盈亏比会变化\n"
                        "- 全凯利仓位波动极大\n"
                        "- 参数估计误差会被放大"
                    ),
                },
            },
        }
