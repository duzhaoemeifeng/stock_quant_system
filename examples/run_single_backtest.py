"""
==================================================
 风险提示：本脚本仅用于量化策略学习与教学演示，
 不构成任何投资建议。回测结果不代表未来收益。
 股市有风险，投资需谨慎。
==================================================
单股完整回测示例：双均线趋势跟踪策略。

运行方式:
    cd stock_quant_system
    python examples/run_single_backtest.py
"""

import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import matplotlib
matplotlib.use("Agg")

from stock_quant_system.data.akshare_source import AKShareSource
from stock_quant_system.data.data_cleaner import DataCleaner
from stock_quant_system.signals.trend_following import DualMACrossoverSignal
from stock_quant_system.portfolio.fixed_sizing import FixedFractionSizer
from stock_quant_system.portfolio.risk_manager import RiskManager
from stock_quant_system.portfolio.stop_loss import FixedStopLoss
from stock_quant_system.portfolio.trailing_stop import TrailingStop
from stock_quant_system.backtest.vectorbt_engine import SimpleBacktestEngine
from stock_quant_system.backtest.slippage import SlippageModel
from stock_quant_system.visualization.dashboard import plot_dashboard


def main():
    symbol = "000001"  # 平安银行
    print(f"=== {symbol} 双均线策略回测 ===\n")

    # 1. 数据下载
    print("下载数据...")
    source = AKShareSource(request_delay=1.0)
    raw = source.download_daily_bars(symbol, "20220101", "20240630", adjust="qfq")
    if raw.empty:
        print("数据下载失败，请检查网络或股票代码")
        return

    # 2. 数据清洗
    cleaner = DataCleaner()
    data = cleaner.pipeline(raw)
    print(f"数据: {len(data)} 个交易日, {data.index[0].date()} ~ {data.index[-1].date()}")

    # 3. 信号生成
    signal_gen = DualMACrossoverSignal({"fast_window": 5, "slow_window": 20})
    signals = signal_gen.generate(data)
    trade_signals = signals[signals["signal"].notna()]
    print(f"信号: {len(trade_signals)} 个交易信号 "
          f"(买入 {(trade_signals['signal']>0).sum()}, "
          f"卖出 {(trade_signals['signal']<0).sum()})")

    # 4. 仓位 + 风控
    sizer = FixedFractionSizer({"fraction": 0.15})
    risk_mgr = (RiskManager()
                .add_rule(FixedStopLoss({"stop_loss_pct": 0.07}), priority=1)
                .add_rule(TrailingStop({"trailing_pct": 0.15}), priority=2))
    slippage = SlippageModel(slippage_pct=0.001, commission_pct=0.0003)

    # 5. 回测
    print("\n执行回测...")
    engine = SimpleBacktestEngine()
    result = engine.run(
        data=data, signals=signals,
        position_sizer=sizer, risk_manager=risk_mgr,
        slippage_model=slippage, initial_capital=1_000_000,
    )

    # 6. 输出
    print(result.summary())

    # 7. 可视化
    print("\n生成图表...")
    out_path = os.path.join(os.path.dirname(__file__), f"backtest_{symbol}.png")
    dashboard = plot_dashboard(result, data=data, title=f"{symbol} 双均线策略回测")
    dashboard.savefig(out_path, dpi=150)
    print(f"图表已保存为 {out_path}")


if __name__ == "__main__":
    main()
