"""
==================================================
 风险提示：本脚本仅用于测试系统功能，
 不构成任何投资建议。
==================================================
端到端回测功能测试（使用合成数据）。
"""

import sys
import os
# 确保 sys.path 包含 stock_quant_system 的父目录
# tests/test_e2e.py -> tests/ -> stock_quant_system/ -> parent(C:/Users/30699)
_parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import numpy as np

from stock_quant_system.signals.trend_following import DualMACrossoverSignal
from stock_quant_system.portfolio.fixed_sizing import FixedFractionSizer
from stock_quant_system.portfolio.risk_manager import RiskManager
from stock_quant_system.portfolio.stop_loss import FixedStopLoss
from stock_quant_system.portfolio.trailing_stop import TrailingStop
from stock_quant_system.portfolio.daily_loss_limit import DailyLossLimit
from stock_quant_system.backtest.vectorbt_engine import SimpleBacktestEngine
from stock_quant_system.backtest.slippage import SlippageModel
from stock_quant_system.visualization.dashboard import plot_dashboard


def test_end_to_end():
    """合成数据 + 完整回测管线测试。"""
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    price = 50.0
    prices = []
    for _ in range(n):
        price *= 1 + np.random.normal(0.0005, 0.018)
        prices.append(price)

    data = pd.DataFrame({
        "open": [p * (1 + np.random.uniform(-0.01, 0)) for p in prices],
        "high": [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        "low": [p * (1 + np.random.uniform(-0.02, 0)) for p in prices],
        "close": prices,
        "volume": np.random.randint(1e7, 1e9, n).astype(float),
    }, index=dates)
    data.index.name = "date"

    print(f"Synthetic data: {len(data)} rows, "
          f"close {data['close'].min():.2f} ~ {data['close'].max():.2f}")

    # 信号
    gen = DualMACrossoverSignal({"fast_window": 5, "slow_window": 20})
    signals = gen.generate(data)
    trade_count = signals["signal"].notna().sum()
    print(f"Signals: {trade_count} (buy={(signals['signal'] > 0).sum()}, "
          f"sell={(signals['signal'] < 0).sum()})")

    # 仓位 + 风控
    sizer = FixedFractionSizer({"fraction": 0.15})
    risk = RiskManager()
    risk.add_rule(FixedStopLoss({"stop_loss_pct": 0.07}), priority=1)
    risk.add_rule(TrailingStop({"trailing_pct": 0.15}), priority=2)
    risk.add_rule(DailyLossLimit({"max_daily_loss_pct": 0.03}), priority=3)

    # 回测
    engine = SimpleBacktestEngine()
    slippage = SlippageModel()
    result = engine.run(
        data=data, signals=signals, position_sizer=sizer,
        risk_manager=risk, slippage_model=slippage,
        initial_capital=1_000_000,
    )

    print(result.summary())

    # 可视化
    fig = plot_dashboard(result, data=data,
                         title="Synthetic Data Backtest")
    out_path = os.path.join(os.path.dirname(__file__), "..",
                            "backtest_synthetic.png")
    fig.savefig(out_path, dpi=100)
    print(f"\nChart saved to {out_path}")

    # 断言
    assert result.equity_curve is not None
    assert len(result.equity_curve) == n
    assert result.trade_count >= 0
    print("\nAll assertions passed. E2E test OK!")


if __name__ == "__main__":
    test_end_to_end()
