"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
自定义异常体系。
"""


class QuantSystemError(Exception):
    """量化系统基础异常。"""
    pass


class DataSourceError(QuantSystemError):
    """数据源异常（下载失败、网络错误、代码无效）。"""
    pass


class DataValidationError(QuantSystemError):
    """数据校验异常（字段缺失、类型错误、价格异常）。"""
    pass


class FactorComputationError(QuantSystemError):
    """因子计算异常（除零、NaN溢出、参数非法）。"""
    pass


class SignalGenerationError(QuantSystemError):
    """信号生成异常（无有效数据、规则冲突）。"""
    pass


class RiskLimitExceeded(QuantSystemError):
    """风控拦截异常（触发止损、日亏损超限）。"""
    pass


class BacktestError(QuantSystemError):
    """回测引擎异常（资金不足、订单拒绝、数据不足）。"""
    pass


class OptimizationError(QuantSystemError):
    """参数优化异常（搜索空间无效、收敛失败）。"""
    pass


class ConfigurationError(QuantSystemError):
    """配置异常（参数非法、文件缺失）。"""
    pass
