"""Quick smoke test - no matplotlib."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np

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

print("Data: %d rows" % len(data))

from stock_quant_system.signals.trend_following import DualMACrossoverSignal
gen = DualMACrossoverSignal({"fast_window": 5, "slow_window": 20})
signals = gen.generate(data)
print("Signals: %d" % signals["signal"].notna().sum())

from stock_quant_system.portfolio.fixed_sizing import FixedFractionSizer
from stock_quant_system.portfolio.risk_manager import RiskManager
from stock_quant_system.portfolio.stop_loss import FixedStopLoss

sizer = FixedFractionSizer({"fraction": 0.15})
risk = RiskManager()
risk.add_rule(FixedStopLoss({"stop_loss_pct": 0.07}), priority=1)

from stock_quant_system.backtest.vectorbt_engine import SimpleBacktestEngine
from stock_quant_system.backtest.slippage import SlippageModel

print("Running backtest...")
engine = SimpleBacktestEngine()
result = engine.run(
    data=data, signals=signals, position_sizer=sizer,
    risk_manager=risk, slippage_model=SlippageModel(),
    initial_capital=1_000_000,
)

print(result.summary())
print("\nQuick test PASSED!")
