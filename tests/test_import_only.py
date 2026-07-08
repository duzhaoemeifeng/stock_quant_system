"""Test imports only - no execution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

print("step 1")
import pandas as pd, numpy as np
print("step 2")
from stock_quant_system.signals.trend_following import DualMACrossoverSignal
print("step 3")
from stock_quant_system.portfolio.fixed_sizing import FixedFractionSizer
print("step 4")
from stock_quant_system.portfolio.risk_manager import RiskManager
print("step 5")
from stock_quant_system.backtest.vectorbt_engine import SimpleBacktestEngine
print("step 6")
from stock_quant_system.backtest.slippage import SlippageModel
print("step 7: all imports OK")

# try creating data and running
data = pd.DataFrame({
    "open": [10.0] * 5, "high": [10.5] * 5, "low": [9.5] * 5,
    "close": [10.0, 10.2, 10.1, 10.3, 10.4], "volume": [1e8] * 5
}, index=pd.date_range("2024-01-01", periods=5, freq="B"))
print("step 8: data created")

signals = pd.DataFrame({
    "signal": [float("nan"), 1.0, float("nan"), -1.0, float("nan")],
    "signal_strength": [0, 1, 0, 1, 0]
}, index=data.index)
print("step 9: signals created")

engine = SimpleBacktestEngine()
print("step 10: engine created, running...")
result = engine.run(
    data=data, signals=signals, position_sizer=None,
    risk_manager=None, slippage_model=SlippageModel()
)
print("step 11: backtest done, return=%.4f" % result.total_return)
print("ALL OK")
