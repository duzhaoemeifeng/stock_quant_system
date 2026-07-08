"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
全局配置模块，使用 dataclass 组织所有可调参数。
"""

from dataclasses import dataclass, field


@dataclass
class DataConfig:
    """数据采集与缓存配置。"""
    cache_dir: str = "./data/cache"
    cache_format: str = "parquet"
    cache_ttl_days: int = 1
    default_adjust: str = "qfq"
    max_retries: int = 3
    request_delay: float = 1.0


@dataclass
class BacktestConfig:
    """回测引擎配置。"""
    initial_capital: float = 1_000_000.0
    commission_pct: float = 0.0003      # 佣金万分之三
    min_commission: float = 5.0          # 最低佣金 5 元
    stamp_tax_pct: float = 0.001         # 印花税千分之一（仅卖出）
    slippage_pct: float = 0.001          # 滑点千分之一


@dataclass
class RiskConfig:
    """风控参数配置。"""
    default_stop_loss: float = 0.07       # 固定止损 7%
    default_trailing_stop: float = 0.15   # 移动止损 15%回撤
    max_daily_loss: float = 0.03          # 单日最大亏损 3%
    max_total_drawdown: float = 0.25      # 总回撤阈值 25%
    max_position_pct: float = 0.20        # 单票最大仓位 20%
    max_open_positions: int = 10          # 最大持仓数
    max_consecutive_losses: int = 5       # 连续亏损暂停交易次数
    volatility_filter_pct: float = 0.03   # 波动率过滤阈值


@dataclass
class Settings:
    """全局设置。"""
    data: DataConfig = field(default_factory=DataConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)


# 模块级单例
settings = Settings()
