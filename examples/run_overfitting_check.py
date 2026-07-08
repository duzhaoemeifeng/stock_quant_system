"""
==================================================
 风险提示：本脚本仅用于量化策略学习与教学演示，
 不构成任何投资建议。
==================================================
过拟合检测示例：样本内/外绩效对比。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.akshare_source import AKShareSource
from data.data_cleaner import DataCleaner
from signals.trend_following import DualMACrossoverSignal
from portfolio.fixed_sizing import FixedFractionSizer
from backtest.vectorbt_engine import SimpleBacktestEngine
from backtest.slippage import SlippageModel
from optimization.overfitting import OverfittingDetector


def main():
    symbol = "000001"
    print(f"=== {symbol} 过拟合检测 ===\n")

    source = AKShareSource(request_delay=1.0)
    raw = source.download_daily_bars(symbol, "20190101", "20240630", adjust="qfq")
    if raw.empty:
        print("数据下载失败")
        return
    data = DataCleaner().pipeline(raw)
    print(f"数据: {len(data)} 个交易日, {data.index[0].date()} ~ {data.index[-1].date()}")

    param_grid = {
        "fast_window": [3, 5, 10],
        "slow_window": [20, 30, 40],
    }

    def signal_fn(data, params):
        return DualMACrossoverSignal(params).generate(data)

    engine = SimpleBacktestEngine()
    sizer = FixedFractionSizer({"fraction": 0.15})
    slippage = SlippageModel()

    detector = OverfittingDetector(engine)
    report = detector.detect(
        data=data, signal_fn=signal_fn,
        param_grid=param_grid,
        in_sample_end="20221231",   # 前4年训练，后1.5年测试
        position_sizer=sizer, slippage_model=slippage,
        initial_capital=1_000_000,
    )

    print(report.summary())


if __name__ == "__main__":
    main()
