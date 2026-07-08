"""
==================================================
 风险提示：本脚本仅用于量化策略学习与教学演示，
 不构成任何投资建议。
==================================================
网格搜索示例：对双均线策略参数进行网格寻优。
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
from optimization.grid_search import GridSearch


def main():
    symbol = "000001"
    print(f"=== {symbol} 双均线参数网格搜索 ===\n")

    # 数据准备
    source = AKShareSource(request_delay=1.0)
    raw = source.download_daily_bars(symbol, "20200101", "20240630", adjust="qfq")
    if raw.empty:
        print("数据下载失败")
        return
    data = DataCleaner().pipeline(raw)
    print(f"数据: {len(data)} 个交易日")

    # 参数网格
    param_grid = {
        "fast_window": [3, 5, 10, 15],
        "slow_window": [20, 30, 40, 60],
    }

    def signal_fn(data, params):
        gen = DualMACrossoverSignal(params)
        return gen.generate(data)

    engine = SimpleBacktestEngine()
    sizer = FixedFractionSizer({"fraction": 0.15})
    slippage = SlippageModel()

    searcher = GridSearch(engine, param_grid, scoring="sharpe_ratio")
    result = searcher.search(
        data=data, signal_fn=signal_fn,
        position_sizer=sizer, slippage_model=slippage,
        initial_capital=1_000_000,
    )

    print(f"\n最优参数: {result.best_params}")
    print(f"最优夏普: {result.best_score:.3f}")
    print(f"\n前5名:")
    print(result.top_n(5).to_string())


if __name__ == "__main__":
    main()
