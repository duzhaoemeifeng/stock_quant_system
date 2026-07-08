"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
因子注册中心，支持自定义因子的注册与发现。
"""

from .base import Factor


class FactorRegistry:
    """因子注册中心（单例模式）。

    所有内置和自定义因子通过此注册中心管理。
    支持装饰器注册和直接注册两种方式。

    使用方法:
        # 方式1：装饰器
        @FactorRegistry.register
        class MyFactor(Factor):
            def compute(self, data):
                ...

        # 方式2：直接注册
        FactorRegistry.add("my_factor", MyFactor)

        # 创建实例
        factor = FactorRegistry.create("SMAFactor", {"window": 20})
    """

    _registry: dict[str, type[Factor]] = {}

    @classmethod
    def register(cls, factor_cls: type[Factor]) -> type[Factor]:
        """装饰器：注册因子类。"""
        cls._registry[factor_cls.__name__] = factor_cls
        return factor_cls

    @classmethod
    def add(cls, name: str, factor_cls: type[Factor]) -> None:
        """手动注册因子类。

        Args:
            name: 因子名称。
            factor_cls: 因子类（需继承 Factor）。
        """
        if not issubclass(factor_cls, Factor):
            raise TypeError(
                f"factor_cls 必须继承 Factor，实际类型: {type(factor_cls)}"
            )
        cls._registry[name] = factor_cls

    @classmethod
    def create(cls, name: str, params: dict | None = None) -> Factor:
        """根据名称创建因子实例。

        Args:
            name: 注册的因子名称。
            params: 因子参数。

        Returns:
            因子实例。

        Raises:
            KeyError: 因子未注册。
        """
        if name not in cls._registry:
            available = ", ".join(cls._registry.keys())
            raise KeyError(
                f"因子 '{name}' 未注册。可用因子: {available}"
            )
        return cls._registry[name](params)

    @classmethod
    def list_factors(cls) -> list[str]:
        """列出所有已注册因子名称。"""
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """清空注册中心（主要用于测试）。"""
        cls._registry.clear()
