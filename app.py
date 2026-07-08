"""
==================================================
 风险提示：本系统所有代码仅供教育及研究目的，
 不构成任何投资建议、买卖建议或投资策略推荐。
 过往业绩不代表未来表现。投资有风险，入市须谨慎。
==================================================
股票量化交易系统 — Streamlit Web UI

启动方式:
    cd stock_quant_system
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from datetime import datetime, timedelta

# Agent 模块 — 将项目根目录加入 sys.path
import sys as _sys
from pathlib import Path as _Path
_project_root = str(_Path(__file__).resolve().parent.parent)
if _project_root not in _sys.path:
    _sys.path.insert(0, _project_root)

TODAY = datetime.now().strftime("%Y-%m-%d")

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="股票量化交易系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 风险声明
# ============================================================
RISK_DISCLAIMER = """
> **⚠️ 风险声明：本系统所有代码仅供教育及研究目的，不构成任何投资建议。
> 过往业绩不代表未来表现。量化模型存在过拟合风险，市场条件变化可能导致策略失效。
> 投资有风险，入市须谨慎。**
"""

st.markdown("# 📈 股票量化交易系统")
st.markdown(RISK_DISCLAIMER)
st.markdown("---")


# ============================================================
# 内置回测引擎 (纯numpy/pandas实现，无外部依赖)
# ============================================================

def compute_sma(series, window):
    """简单移动均线"""
    return series.rolling(window=window, min_periods=window).mean()


def generate_dual_ma_signals(data, fast=5, slow=20):
    """双均线交叉信号"""
    fast_ma = compute_sma(data["close"], fast)
    slow_ma = compute_sma(data["close"], slow)

    signals_df = pd.DataFrame(index=data.index)
    signals_df["signal"] = np.nan
    signals_df["position"] = 0
    signals_df.loc[fast_ma > slow_ma, "position"] = 1
    signals_df.loc[fast_ma < slow_ma, "position"] = -1
    signals_df["signal"] = signals_df["position"].diff()

    # 仅保留交叉点
    signals_df.loc[signals_df["signal"] == 0, "signal"] = np.nan
    return signals_df, fast_ma, slow_ma


def generate_macd_signals(data, fast=12, slow=26, sig=9):
    """MACD信号"""
    close = data["close"]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=sig, adjust=False).mean()
    histogram = macd_line - signal_line

    signals_df = pd.DataFrame(index=data.index)
    signals_df["position"] = 0
    signals_df.loc[macd_line > signal_line, "position"] = 1
    signals_df.loc[macd_line < signal_line, "position"] = -1
    signals_df["signal"] = signals_df["position"].diff()
    signals_df.loc[signals_df["signal"] == 0, "signal"] = np.nan

    return signals_df, macd_line, signal_line, histogram


def run_backtest(data, signals_df, initial_capital=1_000_000,
                 stop_loss_pct=0.07, trailing_stop_pct=0.15,
                 fraction=0.15, commission_pct=0.0003, slippage_pct=0.001):
    """向量化回测引擎"""
    n = len(data)
    closes = data["close"].values

    equity = np.zeros(n)
    cash = np.zeros(n)
    position = np.zeros(n)
    avg_cost = np.zeros(n)

    equity[0] = initial_capital
    cash[0] = initial_capital

    peak_capital = initial_capital
    trades = []
    peak_price = 0.0

    for i in range(1, n):
        price = closes[i]
        sig = signals_df["signal"].iloc[i]

        cash[i] = cash[i - 1]
        position[i] = position[i - 1]
        avg_cost[i] = avg_cost[i - 1]

        # ---- 风控：止损检查 ----
        if position[i] > 0 and avg_cost[i] > 0:
            # 固定止损
            loss_pct = (price - avg_cost[i]) / avg_cost[i]
            if loss_pct < -stop_loss_pct:
                # 强制平仓
                actual_price = price * (1 - slippage_pct)
                proceeds = actual_price * position[i]
                fee = max(proceeds * commission_pct, 5) + proceeds * 0.001  # 含印花税
                cash[i] += proceeds - fee
                pnl = (actual_price - avg_cost[i]) * position[i] - fee
                trades.append({
                    "type": "止损平仓", "date": data.index[i],
                    "price": actual_price, "pnl": pnl,
                })
                position[i] = 0
                avg_cost[i] = 0
                peak_price = 0

            # 移动止损
            if avg_cost[i] > 0:
                peak_price = max(peak_price, price)
                if peak_price > 0 and price < peak_price * (1 - trailing_stop_pct):
                    actual_price = price * (1 - slippage_pct)
                    proceeds = actual_price * position[i]
                    fee = max(proceeds * commission_pct, 5) + proceeds * 0.001
                    cash[i] += proceeds - fee
                    pnl = (actual_price - avg_cost[i]) * position[i] - fee
                    trades.append({
                        "type": "移动止损", "date": data.index[i],
                        "price": actual_price, "pnl": pnl,
                    })
                    position[i] = 0
                    avg_cost[i] = 0
                    peak_price = 0

        # ---- 信号处理 ----
        if pd.notna(sig) and sig != 0:
            if sig > 0 and position[i] == 0:
                # 买入
                target_shares = int(cash[i] * fraction / price)
                target_shares = (target_shares // 100) * 100
                if target_shares >= 100:
                    actual_price = price * (1 + slippage_pct)
                    cost = actual_price * target_shares
                    fee = max(cost * commission_pct, 5)
                    total_cost = cost + fee
                    if total_cost <= cash[i]:
                        cash[i] -= total_cost
                        position[i] = target_shares
                        avg_cost[i] = actual_price
                        peak_price = actual_price

            elif sig < 0 and position[i] > 0:
                # 卖出
                actual_price = price * (1 - slippage_pct)
                proceeds = actual_price * position[i]
                fee = max(proceeds * commission_pct, 5) + proceeds * 0.001
                cash[i] += proceeds - fee
                pnl = (actual_price - avg_cost[i]) * position[i] - fee
                trades.append({
                    "type": "信号平仓", "date": data.index[i],
                    "price": actual_price, "pnl": pnl,
                })
                position[i] = 0
                avg_cost[i] = 0
                peak_price = 0

        equity[i] = cash[i] + position[i] * price
        peak_capital = max(peak_capital, equity[i])

    # 结果计算
    equity_s = pd.Series(equity, index=data.index)
    daily_rets = pd.Series(
        np.diff(equity) / equity[:-1], index=data.index[1:]
    )

    total_return = (equity[-1] / initial_capital) - 1.0
    ann_return = (1 + total_return) ** (252 / n) - 1 if n > 0 else 0
    ann_vol = daily_rets.std() * np.sqrt(252) if len(daily_rets) > 0 else 0
    sharpe = (ann_return - 0.03) / ann_vol if ann_vol > 0 else 0

    peak = equity_s.expanding().max()
    drawdown_series = (equity_s - peak) / peak
    max_dd = drawdown_series.min()
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    # 交易统计
    trade_pnls = [t["pnl"] for t in trades if t["type"] == "信号平仓"]
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p < 0]

    result = {
        "equity_curve": equity_s,
        "daily_returns": daily_rets,
        "drawdown_curve": drawdown_series,
        "total_return": total_return,
        "annual_return": ann_return,
        "annual_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "calmar_ratio": calmar,
        "max_drawdown": max_dd,
        "trade_count": len(trades),
        "trades": trades,
        "final_equity": equity[-1],
        "trade_pnls": trade_pnls,
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": len(wins) / len(trade_pnls) if trade_pnls else 0,
        "avg_win": np.mean(wins) if wins else 0,
        "avg_loss": np.mean(losses) if losses else 0,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else float("inf"),
    }
    return result


# ============================================================
# 数据生成
# ============================================================

@st.cache_data(ttl=3600)
def load_data(symbol, use_real_data):
    """加载/生成股票数据"""
    if use_real_data:
        from stock_quant_system.data.data_cleaner import DataCleaner
        cleaner = DataCleaner()
        end_date = datetime.now().strftime("%Y%m%d")

        # 优先尝试 BaoStock
        try:
            from stock_quant_system.data.baostock_source import BaoStockSource
            source = BaoStockSource(request_delay=0.3)
            raw = source.download_daily_bars(symbol, "20190101", end_date, adjust="qfq")
            if raw is not None and not raw.empty:
                return cleaner.pipeline(raw)
        except Exception:
            pass

        # 回退到 AKShare
        try:
            from stock_quant_system.data.akshare_source import AKShareSource
            source = AKShareSource(request_delay=0.5)
            raw = source.download_daily_bars(symbol, "20190101", end_date, adjust="qfq")
            if raw is not None and not raw.empty:
                return cleaner.pipeline(raw)
        except Exception as e:
            st.warning(f"实盘数据获取失败，使用模拟数据: {e}")

    # 模拟数据 — 日期到今时今日
    np.random.seed(hash(symbol) % 2**31)
    n = 1200
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=n, freq="B")
    prices = [50.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0.0003, 0.02)))
    prices = np.array(prices)

    return pd.DataFrame({
        "open": [p * (1 + np.random.uniform(-0.01, 0)) for p in prices],
        "high": [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        "low": [p * (1 + np.random.uniform(-0.02, 0)) for p in prices],
        "close": prices,
        "volume": np.random.randint(1e7, 1e9, n).astype(float),
    }, index=dates)


# ============================================================
# 可视化函数
# ============================================================

def plot_equity_drawdown(result):
    """权益曲线 + 回撤"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                    gridspec_kw={"height_ratios": [2.5, 1]})

    equity = result["equity_curve"]
    initial = equity.iloc[0]
    ax1.plot(equity.index, equity / initial, color="#2196F3", linewidth=1.5)
    ax1.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    ax1.set_title("权益曲线", fontsize=13, fontweight="bold")
    ax1.set_ylabel("净值")
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    dd = result["drawdown_curve"] * 100
    ax2.fill_between(dd.index, 0, dd, color="#F44336", alpha=0.3)
    ax2.plot(dd.index, dd, color="#D32F2F", linewidth=0.8)
    ax2.set_title("回撤曲线", fontsize=11)
    ax2.set_ylabel("回撤 (%)")
    ax2.grid(True, alpha=0.3)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0f}%"))

    fig.tight_layout()
    return fig


def plot_trade_pnl(result):
    """盈亏分布"""
    fig, ax = plt.subplots(figsize=(8, 4))
    pnls = result["trade_pnls"]
    if pnls:
        ax.hist(pnls, bins=20, color="#2196F3", alpha=0.7, edgecolor="white")
        ax.axvline(x=np.mean(pnls), color="#FF9800", linestyle="--", linewidth=2)
        ax.axvline(x=0, color="gray", linestyle=":", linewidth=1)
    ax.set_title("逐笔盈亏分布", fontsize=11, fontweight="bold")
    ax.set_xlabel("盈亏 (元)")
    ax.set_ylabel("频次")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    return fig


def plot_signals(data, signals_df, fast_ma, slow_ma):
    """价格+均线+信号标记"""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(data.index, data["close"], color="#333333", linewidth=0.8, alpha=0.7, label="收盘价")
    ax.plot(fast_ma.index, fast_ma, color="#4CAF50", linewidth=1.0, label=f"快线 MA({len(fast_ma.dropna())})")
    ax.plot(slow_ma.index, slow_ma, color="#F44336", linewidth=1.0, label=f"慢线 MA({len(slow_ma.dropna())})")

    buy_signals = signals_df[signals_df["signal"] > 0]
    sell_signals = signals_df[signals_df["signal"] < 0]

    if len(buy_signals) > 0:
        ax.scatter(buy_signals.index, data.loc[buy_signals.index, "close"],
                   marker="^", s=80, color="#4CAF50", zorder=5, label="买入", edgecolors="white")
    if len(sell_signals) > 0:
        ax.scatter(sell_signals.index, data.loc[sell_signals.index, "close"],
                   marker="v", s=80, color="#F44336", zorder=5, label="卖出", edgecolors="white")

    ax.set_title("价格走势与交易信号", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


# ============================================================
# 侧边栏
# ============================================================

st.sidebar.markdown("## ⚙️ 策略配置")

symbol = st.sidebar.text_input("股票代码", value="000001", help="A股6位代码，如000001(平安银行)")
use_real = st.sidebar.checkbox("使用实盘数据(AKShare)", value=False,
                               help="勾选后从网络下载真实数据，否则使用模拟数据演示")

st.sidebar.markdown("### 📊 策略类型")
strategy_type = st.sidebar.selectbox("选择策略", ["双均线交叉", "MACD"])

st.sidebar.markdown("### 📐 策略参数")
if strategy_type == "双均线交叉":
    fast_window = st.sidebar.slider("快线周期", 3, 30, 5)
    slow_window = st.sidebar.slider("慢线周期", 10, 120, 20)
else:
    macd_fast = st.sidebar.slider("MACD快线", 8, 20, 12)
    macd_slow = st.sidebar.slider("MACD慢线", 20, 40, 26)
    macd_sig = st.sidebar.slider("信号线", 5, 15, 9)

st.sidebar.markdown("### 💰 仓位管理")
position_pct = st.sidebar.slider("单次仓位比例(%)", 5, 30, 15) / 100

st.sidebar.markdown("### 🛡️ 风控参数")
stop_loss = st.sidebar.slider("固定止损(%)", 3, 15, 7) / 100
trailing_stop = st.sidebar.slider("移动止损(%)", 5, 30, 15) / 100

st.sidebar.markdown("### 💵 交易成本")
commission = st.sidebar.slider("佣金(万分之)", 1.0, 5.0, 3.0) / 10000
slippage = st.sidebar.slider("滑点(千分之)", 0.0, 3.0, 1.0) / 1000

initial_capital = st.sidebar.number_input("初始资金(万元)", min_value=10, max_value=1000, value=100) * 10000

# 运行按钮
run_btn = st.sidebar.button("🚀 开始回测", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown(RISK_DISCLAIMER)


# ============================================================
# 主页面 — 两个标签页
# ============================================================

tab1, tab2, tab3 = st.tabs(["📊 手动回测", "🤖 AI Agent 智能分析", "💬 对话 Agent"])

# ============================================================
# Tab 1: 手动回测
# ============================================================
with tab1:
    if run_btn:
        with st.spinner("加载数据..."):
            data = load_data(symbol, use_real)

        if data.empty:
            st.error("数据加载失败")
            st.stop()

        st.success(f"数据加载完成：{len(data)} 个交易日，"
                   f"{data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}")

        # 策略信号
        with st.spinner("生成交易信号..."):
            if strategy_type == "双均线交叉":
                signals_df, fast_ma, slow_ma = generate_dual_ma_signals(
                    data, fast_window, slow_window
                )
            else:
                signals_df, macd_line, signal_line, histogram = generate_macd_signals(
                    data, macd_fast, macd_slow, macd_sig
                )
                fast_ma = macd_line
                slow_ma = signal_line

        buy_count = int((signals_df["signal"] > 0).sum())
        sell_count = int((signals_df["signal"] < 0).sum())

        # 回测
        with st.spinner("执行回测..."):
            result = run_backtest(
                data, signals_df,
                initial_capital=initial_capital,
                stop_loss_pct=stop_loss,
                trailing_stop_pct=trailing_stop,
                fraction=position_pct,
                commission_pct=commission,
                slippage_pct=slippage,
            )

        # ============================================================
        # 结果展示
        # ============================================================

        st.markdown("---")
        st.markdown("## 📊 回测结果")

        # 核心指标卡片
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("累计收益率", f"{result['total_return']:.2%}")
        col2.metric("年化收益率", f"{result['annual_return']:.2%}")
        col3.metric("夏普比率", f"{result['sharpe_ratio']:.2f}")
        col4.metric("最大回撤", f"{result['max_drawdown']:.2%}")
        col5.metric("胜率", f"{result['win_rate']:.1%}")
        col6.metric("交易次数", str(result['trade_count']))

        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("年化波动率", f"{result['annual_volatility']:.2%}")
        col2.metric("卡玛比率", f"{result['calmar_ratio']:.2f}")
        col3.metric("盈利因子", f"{result['profit_factor']:.2f}" if result['profit_factor'] != float("inf") else "∞")
        col4.metric("最终权益", f"{result['final_equity']:,.0f}")

        st.markdown("---")

        # 图表
        st.markdown("### 📈 权益曲线与回撤")
        fig1 = plot_equity_drawdown(result)
        st.pyplot(fig1)
        plt.close(fig1)

        st.markdown("### 🎯 交易信号标记")
        fig2 = plot_signals(data, signals_df, fast_ma, slow_ma)
        st.pyplot(fig2)
        plt.close(fig2)

        st.markdown("### 📊 盈亏分布")
        fig3 = plot_trade_pnl(result)
        st.pyplot(fig3)
        plt.close(fig3)

        # 策略参数总结
        st.markdown("---")
        st.markdown("## 📋 策略配置总结")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **策略设置**
            - 策略类型: {strategy_type}
            - 股票代码: {symbol}
            - 初始资金: {initial_capital:,.0f} 元
            - 数据量: {len(data)} 个交易日
            """)
        with col2:
            st.markdown(f"""
            **风控设置**
            - 固定止损: {stop_loss:.1%}
            - 移动止损: {trailing_stop:.1%}
            - 仓位比例: {position_pct:.1%}
            - 佣金: {commission:.3%} | 滑点: {slippage:.1%}
            """)

        # 信号统计
        st.markdown("### 🚦 信号统计")
        st.info(f"买入信号: **{buy_count}** 次 | 卖出信号: **{sell_count}** 次 | "
                f"盈利交易: **{result['win_count']}** 次 | 亏损交易: **{result['loss_count']}** 次")

        if result['win_count'] > 0 or result['loss_count'] > 0:
            st.info(f"平均盈利: **{result['avg_win']:,.0f}** 元 | "
                    f"平均亏损: **{result['avg_loss']:,.0f}** 元 | "
                    f"盈亏比: **{abs(result['avg_win'] / result['avg_loss']) if result['avg_loss'] != 0 else '∞':}**")

        st.markdown("---")
        st.markdown("## ⚠️ 策略缺陷与过拟合风险")
        st.warning("""
        **过拟合检测要点：**
        1. **参数敏感**: 均线周期等参数改变后结果可能剧烈变化 → 需网格搜索找稳定参数区间
        2. **市场适应**: 趋势策略在震荡市频繁亏损，单边市场表现好 → 需配合市场状态过滤器
        3. **样本偏差**: 回测区间有限，数据量少时统计指标不可靠 → 建议至少2年以上数据
        4. **前视偏差**: 确保所有指标计算使用历史数据（`shift()`对齐）
        5. **滑点低估**: 实盘滑点可能远超模型假设，尤其是流动性差的股票

        **改进方向：**
        - 多周期组合降低参数敏感度
        - 添加波动率过滤器（高波动暂停交易）
        - 样本外验证（最后20%数据不参与调参）
        - 网格搜索+交叉验证寻找稳健参数
        """)

    else:
        # 默认显示：系统介绍
        st.markdown("## 🏗️ 系统架构")

        st.markdown("""
        本系统是一个完整的 **A股量化交易回测框架**，采用模块化架构设计，支持：

        | 模块 | 功能 | 技术实现 |
        |------|------|----------|
        | 📡 数据采集 | A股日线下载、数据清洗、本地缓存 | AKShare |
        | 📊 因子计算 | MA/MACD/RSI/BOLL/ATR/ROC等12+因子 | numpy/pandas |
        | 🎯 信号生成 | 趋势跟踪、均值回归、多因子打分 | 可扩展引擎 |
        | 💰 仓位管理 | 固定仓位、ATR动态、凯利公式 | 三种模型 |
        | 🛡️ 风控系统 | 固定止损、移动止损、日内限制 | 风控链 |
        | 📈 回测引擎 | 向量化回测、A股T+1、滑点手续费 | numpy向量化 |
        | 📉 可视化 | 权益曲线、回撤图、信号标记 | matplotlib |
        | 🔍 参数优化 | 网格搜索、敏感性分析、过拟合检测 | 样本内外对比 |
        | 🤖 AI Agent | 市场诊断、策略推荐、自动优化 | 智能分析引擎 |
        """)

        st.markdown("### 📂 项目结构")
        st.code("""
stock_quant_system/
├── agent/           # AI 量化交易 Agent
├── config/          # 全局配置
├── data/            # 数据采集与清洗
├── factors/         # 技术指标因子库(12+)
├── signals/         # 信号生成引擎
├── portfolio/       # 仓位管理与风控
├── backtest/        # 回测引擎
├── optimization/    # 参数优化
├── visualization/   # 可视化工具
├── live/            # 实盘接口定义
├── examples/        # 示例脚本
└── app.py           # Web界面 ← 当前页面
        """)

        st.info("👈 **在左侧边栏设置参数，然后点击「开始回测」按钮**")

# ============================================================
# Tab 2: AI Agent 智能分析
# ============================================================
with tab2:
    st.markdown("## 🤖 AI 量化交易 Agent")
    st.markdown("""
    Agent 会自动完成以下步骤：
    1. **市场状态诊断** — 识别趋势/震荡/波动率状态
    2. **策略智能推荐** — 根据市场状态选择最优策略
    3. **参数自动优化** — 网格搜索最佳参数组合
    4. **综合报告生成** — 输出完整的分析报告
    """)

    agent_symbol = st.text_input("分析股票代码", value="000001", key="agent_symbol")
    agent_use_real = st.checkbox("使用实盘数据", value=False, key="agent_real",
                                  help="勾选后通过AKShare下载真实A股数据")
    agent_run = st.button("🤖 启动 Agent 分析", type="primary")

    if agent_run:
        # 加载数据
        with st.spinner("📡 Agent 正在加载数据..."):
            agent_data = load_data(agent_symbol, agent_use_real)

        if agent_data.empty:
            st.error("数据加载失败")
            st.stop()

        st.success(f"数据就绪: {len(agent_data)} 个交易日, "
                   f"{agent_data.index[0].strftime('%Y-%m-%d')} ~ {agent_data.index[-1].strftime('%Y-%m-%d')}")

        # 导入 Agent
        try:
            from stock_quant_system.agent.quant_agent import QuantAgent
            from stock_quant_system.agent.strategy_selector import StrategySelector
        except ImportError:
            st.error("Agent 模块加载失败，请检查 agent/ 目录")
            st.stop()

        # 步骤1: 市场诊断
        with st.spinner("🔍 Agent 正在诊断市场状态..."):
            agent = QuantAgent()
            quick = agent.quick_scan(agent_data)

        st.markdown("---")
        st.markdown("### 🔍 市场状态诊断")

        regime = quick["market_regime"]
        reco = quick["recommendation"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("市场状态", regime["regime_label"])
        col2.metric("ADX", f"{regime['adx']:.1f}", delta="有趋势" if regime["adx"] > 25 else "无趋势")
        col3.metric("波动率", f"{regime['volatility']:.1%}", delta=regime["volatility_label"])
        col4.metric("风险等级", regime["risk_level"])

        col1, col2, col3 = st.columns(3)
        col1.metric("RSI(14)", f"{regime['rsi']:.1f}",
                    delta="超买" if regime["rsi"] > 70 else ("超卖" if regime["rsi"] < 30 else "中性"))
        col2.metric("建议仓位", f"{regime['recommended_position']:.0%}")
        col3.metric("波动率分位", f"{regime['vol_percentile']:.0%}")

        st.info(regime["description"])

        # 步骤2: 策略推荐
        st.markdown("---")
        st.markdown("### 🎯 策略推荐")

        st.success(f"**推荐策略**: {reco['primary']}")
        st.markdown(f"**推荐理由**: {reco.get('reason', 'N/A')}")

        col1, col2, col3 = st.columns(3)
        col1.metric("仓位模型", reco.get("position_model", "fixed"))
        col2.metric("止损设置", f"{reco.get('stop_loss', 0.05):.0%}")
        col3.metric("建议仓位", f"{reco.get('recommended_position', 0.15):.0%}")

        st.markdown("**推荐参数**:")
        st.json(reco.get("params", {}))

        # 步骤3: 参数优化
        st.markdown("---")
        with st.spinner("🔧 Agent 正在优化参数..."):
            full_result = agent.analyze(agent_data, symbol=agent_symbol)

        opt = full_result.get("optimization")
        if opt and opt.get("best_params"):
            st.markdown("### 🔧 参数优化结果")
            st.success(f"测试了 **{opt.get('n_tested', 0)}** 组参数组合")

            col1, col2, col3 = st.columns(3)
            col1.metric("样本内夏普", f"{opt.get('best_sharpe_in', 0):.3f}")
            col2.metric("样本外夏普", f"{opt.get('best_sharpe_out', 0):.3f}")
            col3.metric("夏普衰减", f"{opt.get('sharpe_drop', 0):.3f}",
                        delta="⚠️ 过拟合" if opt.get("is_overfitted") else "✅ 稳健",
                        delta_color="inverse" if opt.get("is_overfitted") else "normal")

            st.markdown("**最优参数**:")
            st.json(opt["best_params"])

            # Top 5
            st.markdown("**Top 5 参数组合**:")
            if "top5" in opt and opt["top5"]:
                top5_data = []
                for r in opt["top5"]:
                    row = {k: v for k, v in r.items() if not k.endswith("_in") and k != "sharpe_drop"}
                    top5_data.append(row)
                st.dataframe(pd.DataFrame(top5_data), use_container_width=True)

            # 敏感性
            st.markdown("**参数敏感性**（越敏感越需谨慎调参）:")
            for param, sens in sorted(opt.get("sensitivity", {}).items(),
                                       key=lambda x: x[1], reverse=True):
                bar_len = min(int(sens * 50), 30)
                bar = "█" * bar_len
                st.markdown(f"`{param}`: {bar} ({sens:.3f})")

        # 步骤4: 完整报告
        st.markdown("---")
        st.markdown("### 📋 完整分析报告")
        with st.expander("展开查看完整报告", expanded=False):
            st.markdown(full_result.get("report", "报告生成失败"))

        # 所有策略列表
        st.markdown("---")
        st.markdown("### 📚 策略知识库")
        with st.expander("查看所有可用策略"):
            strategies = StrategySelector.list_all_strategies()
            for name, info in strategies.items():
                st.markdown(f"""
                **{name}**
                - 适用场景: {info['适用']}
                - 信号类型: {info['信号类型']}
                - 特点: {info['特点']}
                ---
                """)

    else:
        st.info("👆 **输入股票代码，点击「启动 Agent 分析」查看 AI 智能分析结果**")

        # 展示 Agent 能力
        st.markdown("### 🤖 Agent 核心能力")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **市场状态诊断**
            - 趋势识别（ADX 趋势强度）
            - 波动率分位分析
            - RSI 超买超卖检测
            - 自动计算建议仓位
            - 风险等级评估
            """)
        with col2:
            st.markdown("""
            **智能决策**
            - 5种策略自动匹配
            - 参数网格自动搜索
            - 样本内外交叉验证
            - 过拟合风险检测
            - 完整中文分析报告
            """)

# ============================================================
# Tab 3: 对话 Agent
# ============================================================
with tab3:
    st.markdown("## 💬 对话式量化 Agent")
    st.markdown("用自然语言跟我聊股票分析，试试问：「分析一下茅台」「推荐什么策略」「什么是夏普比率」")

    # 初始化
    if "chat_agent" not in st.session_state:
        st.session_state.chat_agent = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_col1, chat_col2, chat_col3 = st.columns([2, 1, 1])
    with chat_col1:
        chat_symbol = st.text_input("股票代码", value="000001", key="chat_symbol_input")
    with chat_col2:
        chat_load = st.button("📥 加载数据", key="chat_load_btn")
    with chat_col3:
        if st.button("🗑️ 清空", key="chat_clear_btn"):
            st.session_state.chat_history = []
            st.rerun()

    if chat_load:
        with st.spinner("Agent 正在加载数据..."):
            chat_data = load_data(chat_symbol, use_real_data=False)
            if not chat_data.empty:
                from stock_quant_system.agent.chat_agent import ChatAgent
                agent = ChatAgent()
                agent.load_data(chat_symbol, chat_data)
                st.session_state.chat_agent = agent
                st.session_state.chat_history = []
                welcome = agent.respond("你好")
                st.session_state.chat_history.append({"role": "agent", "content": welcome})
                st.success(f"✅ {agent.symbol_name}({chat_symbol}) 已加载！")
                st.rerun()

    st.markdown("---")
    chat_container = st.container(height=420)

    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").markdown(msg["content"])
            else:
                st.chat_message("assistant", avatar="🤖").markdown(msg["content"])

    st.markdown("---")
    user_input = st.chat_input("输入问题，例如「分析一下这只股票」...")

    if user_input:
        if st.session_state.chat_agent is None:
            with st.spinner("初始化 Agent..."):
                data = load_data(chat_symbol, use_real_data=False)
                from stock_quant_system.agent.chat_agent import ChatAgent
                agent = ChatAgent()
                agent.load_data(chat_symbol, data)
                st.session_state.chat_agent = agent

        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("🤖 思考中..."):
            reply = st.session_state.chat_agent.respond(user_input)
        st.session_state.chat_history.append({"role": "agent", "content": reply})
        st.rerun()

    if st.session_state.chat_agent is not None:
        st.markdown("**快捷提问**:")
        qs = ["分析一下这只股票", "现在市场怎么样", "推荐什么策略", "怎么控制风险"]
        for i, q in enumerate(qs):
            if st.button(q, key=f"qq_{i}"):
                st.session_state.chat_history.append({"role": "user", "content": q})
                reply = st.session_state.chat_agent.respond(q)
                st.session_state.chat_history.append({"role": "agent", "content": reply})
                st.rerun()
    else:
        st.info("👆 先点击「📥 加载数据」加载股票数据，然后就可以自由对话！")

st.markdown("---")
st.markdown(RISK_DISCLAIMER)
