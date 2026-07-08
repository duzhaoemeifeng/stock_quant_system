# 股票量化交易系统

> **风险声明：本系统所有代码仅供教育及研究目的，不构成任何投资建议、买卖建议或投资策略推荐。过往业绩不代表未来表现。量化模型存在过拟合风险，市场条件变化可能导致策略失效。投资有风险，入市须谨慎。**

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行单股回测示例
cd examples
python run_single_backtest.py

# 因子库演示
python run_factor_demo.py

# 网格搜索
python run_grid_search.py

# 过拟合检测
python run_overfitting_check.py
```

## 项目结构

```
stock_quant_system/
├── config/             # 全局配置
│   ├── settings.py     # DataConfig, BacktestConfig, RiskConfig
│   └── symbols.py      # 股票池定义
├── data/               # 数据采集
│   ├── base.py         # 统一Schema + Abstract DataSource
│   ├── akshare_source.py  # AKShare A股数据源
│   ├── data_cleaner.py    # 数据清洗
│   └── cache_manager.py   # 本地缓存
├── factors/            # 技术指标因子库
│   ├── base.py         # Abstract Factor
│   ├── registry.py     # 因子注册中心
│   ├── technical.py    # SMA, EMA, MACD, RSI, BOLL, ATR
│   ├── momentum.py     # ROC, Momentum
│   └── volatility.py   # 历史波动率
├── signals/            # 信号生成引擎
│   ├── trend_following.py    # 双均线, MACD
│   ├── mean_reversion.py     # RSI, 布林带
│   ├── multi_factor_scorer.py # 多因子打分
│   └── filter_chain.py       # 信号过滤链
├── portfolio/          # 仓位与风控
│   ├── fixed_sizing.py   # 固定仓位
│   ├── atr_sizing.py     # ATR动态仓位
│   ├── kelly_sizing.py   # 凯利公式
│   ├── stop_loss.py      # 固定止损
│   ├── trailing_stop.py  # 移动止损
│   ├── daily_loss_limit.py # 日内/总回撤限制
│   └── risk_manager.py   # 风控管理器
├── backtest/           # 回测引擎
│   ├── vectorbt_engine.py  # 向量化回测
│   ├── result.py      # BacktestResult
│   ├── metrics.py     # Sharpe, Calmar...
│   └── slippage.py    # 滑点+手续费
├── optimization/       # 参数优化
│   ├── grid_search.py    # 网格搜索
│   ├── sensitivity.py    # 敏感性分析
│   └── overfitting.py    # 过拟合检测
├── visualization/      # 可视化
│   ├── equity_curve.py   # 权益曲线
│   ├── drawdown.py       # 回撤曲线
│   ├── trades.py         # 买卖点标记
│   ├── pnl_histogram.py  # 盈亏分布
│   ├── signal_scatter.py # 信号散点图
│   └── dashboard.py      # 综合看板
├── live/               # 实盘接口(仅抽象定义)
├── examples/           # 示例脚本
└── utils/              # 工具
```

## 核心特性

- **统一数据Schema**: AKShare/yfinance 自动映射为标准列名
- **因子注册中心**: @FactorRegistry.register 装饰器支持热插拔自定义因子
- **多类型信号**: 趋势跟踪、均值回归、多因子打分
- **三种仓位模型**: 固定比例、ATR动态、凯利公式
- **可组合风控**: FixedStopLoss + TrailingStop + DailyLossLimit 自由组合
- **标准化回测输出**: 统一的 BacktestResult，不依赖特定引擎
- **参数优化**: 网格搜索、敏感性分析、过拟合检测

## 自定义因子

```python
from factors.base import Factor
from factors.registry import FactorRegistry

@FactorRegistry.register
class MyFactor(Factor):
    def compute(self, data):
        return data["close"].pct_change(20)
```

## 可调超参数

| 模块 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| 双均线 | fast_window | 5 | 快线周期 |
| 双均线 | slow_window | 20 | 慢线周期 |
| RSI | window | 14 | 计算周期 |
| RSI | oversold/overbought | 30/70 | 超买超卖阈值 |
| 布林带 | window/num_std | 20/2.0 | 窗口和标准差倍数 |
| 固定仓位 | fraction | 0.10 | 每次交易资金比例 |
| ATR仓位 | risk_pct | 0.02 | 单笔风险比例 |
| 凯利仓位 | fraction | 0.25 | 分数凯利系数 |
| 止损 | stop_loss_pct | 0.07 | 固定止损比例 |
| 移动止损 | trailing_pct | 0.15 | 从峰值回撤比例 |
| 日内限制 | max_daily_loss_pct | 0.03 | 单日最大亏损比例 |

## 策略缺陷与过拟合风险

1. **趋势策略**：震荡市中频繁假信号 → 添加波动率过滤器
2. **均线策略**：参数过度敏感 → 使用多周期组合降低过拟合
3. **多因子打分**：因子共线性 → 正交化处理或降维
4. **网格搜索**：参数过拟合 → 必须做样本外验证
5. **回测偏差**：前视偏差、幸存者偏差 → 严格使用shift() 对齐信号与价格
```
