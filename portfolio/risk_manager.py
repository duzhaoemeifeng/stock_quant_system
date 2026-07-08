"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。风控机制不能完全消除投资风险，
 极端行情下可能产生超出预期的损失。
==================================================
风控管理器：组合模式，按优先级依次执行所有风控规则。
"""

from .base import RiskContext, RiskDecision, RiskRule


class RiskManager:
    """风控管理器。

    将多个 RiskRule 组合成风控链，按优先级排序后依次检查。
    任一规则拒绝即拦截交易。

    使用方法:
        rm = RiskManager()
        rm.add_rule(FixedStopLoss({"stop_loss_pct": 0.07}), priority=1)
        rm.add_rule(TrailingStop({"trailing_pct": 0.15}), priority=2)
        rm.add_rule(DailyLossLimit({"max_daily_loss_pct": 0.03}), priority=3)

        decision = rm.check_all(context)
    """

    def __init__(self):
        self._rules: list[tuple[RiskRule, int]] = []

    def add_rule(self, rule: RiskRule, priority: int = 0) -> "RiskManager":
        """添加风控规则。

        Args:
            rule: 风控规则实例。
            priority: 优先级（数字越小越先执行）。

        Returns:
            self（链式调用）。
        """
        self._rules.append((rule, priority))
        self._rules.sort(key=lambda x: x[1])
        return self

    def remove_rule(self, rule_name: str) -> "RiskManager":
        """按名称移除规则。"""
        self._rules = [
            (r, p) for r, p in self._rules if r.name != rule_name
        ]
        return self

    def check_all(self, context: RiskContext) -> RiskDecision:
        """依次检查所有风控规则。

        Args:
            context: 风控上下文。

        Returns:
            RiskDecision，如果所有规则通过则 approved=True，
            否则返回第一个拒绝的决策。
        """
        for rule, _ in self._rules:
            decision = rule.check(context)
            if not decision.approved:
                return decision
        return RiskDecision(approved=True)

    @property
    def rules_list(self) -> list[str]:
        """返回已注册的规则名称列表。"""
        return [r.name for r, _ in self._rules]

    def __len__(self) -> int:
        return len(self._rules)
