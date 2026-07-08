"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。技术指标基于历史价格计算，
 不具备预测未来价格的能力。
==================================================
因子库入口。
"""

from .base import Factor, FactorResult
from .registry import FactorRegistry

# 导入因子模块以触发注册
from . import technical  # noqa: F401
from . import momentum   # noqa: F401
from . import volatility # noqa: F401
