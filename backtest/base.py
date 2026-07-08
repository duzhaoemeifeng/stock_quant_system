"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
回测引擎抽象基类。
"""

from abc import ABC, abstractmethod

import pandas as pd

from .result import BacktestResult
from .slippage import SlippageModel
from ..portfolio.base import PositionSizer
from ..portfolio.risk_manager import RiskManager


class BacktestEngine(ABC):
    """回测引擎抽象基类。

    所有回测引擎需实现 run 方法，返回标准化的 BacktestResult。

    风险提示：回测结果是基于历史数据的模拟，不保证未来收益。
    过拟合、幸存者偏差、前视偏差等均可能导致回测结果失真。
    """

    @abstractmethod
    def run(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame,
        position_sizer: PositionSizer | None = None,
        risk_manager: RiskManager | None = None,
        slippage_model: SlippageModel | None = None,
        initial_capital: float = 1_000_000.0,
    ) -> BacktestResult:
        """执行回测。

        Args:
            data: 统一 Schema OHLCV DataFrame。
            signals: 交易信号 DataFrame，至少包含 'signal' 列。
            position_sizer: 仓位计算器。
            risk_manager: 风控管理器。
            slippage_model: 滑点与手续费模型。
            initial_capital: 初始资金。

        Returns:
            标准化的 BacktestResult。
        """
        ...
