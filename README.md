# 📈 股票量化交易系统

> **⚠️ 风险声明：本系统所有代码仅供教育及研究目的，不构成任何投资建议、买卖建议或投资策略推荐。过往业绩不代表未来表现。量化模型存在过拟合风险，市场条件变化可能导致策略失效。投资有风险，入市须谨慎。**

## 项目简介

本系统是一套**模块化的 A 股量化交易研究平台**，覆盖"数据采集 → 因子计算 → 信号生成 → 仓位管理 → 回测评估 → 参数优化 → AI 分析"的完整研究链路。内置 Streamlit Web 交互界面和对话式 AI Agent，适合量化策略的学习、研究与快速验证。

## 快速开始

**环境要求：Python >= 3.10**

```bash
# 1. 克隆项目
git clone https://github.com/duzhaoemeifeng/stock_quant_system.git
cd stock_quant_system

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Web 界面
streamlit run app.py
# 如果 streamlit 命令找不到，使用：
# python -m streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`，即可通过界面进行策略回测、因子分析、参数优化。

## 命令行示例

```bash
# 单股回测（含可视化图表）
cd examples
python run_single_backtest.py

# 因子库演示
python run_factor_demo.py

# 网格搜索参数优化
python run_grid_search.py

# 过拟合检测
python run_overfitting_check.py
```

## 项目架构

```
stock_quant_system/
│
├── app.py                  # Streamlit Web UI 主入口（1038行自包含回测引擎+UI）
│
├── config/                 # 全局配置
│   ├── settings.py         # DataConfig, BacktestConfig, RiskConfig
│   └── symbols.py          # 股票池定义
│
├── data/                   # 数据层
│   ├── data_schema.py      # 统一数据 Schema（OHLCV 标准列名）
│   ├── akshare_source.py   # AKShare A 股数据源（复权/日线/分钟）
│   ├── data_cleaner.py     # 缺失值/异常值检测与清洗
│   └── cache_manager.py    # Parquet 本地缓存（支持 TTL 过期）
│
├── factors/                # 因子库（可扩展注册中心）
│   ├── base.py             # 抽象因子基类
│   ├── registry.py         # 因子注册中心（装饰器注册 + 动态创建）
│   ├── technical.py        # SMA, EMA, MACD, RSI, BOLL, ATR
│   ├── momentum.py         # ROC, Momentum 动量因子
│   └── volatility.py       # 历史波动率因子
│
├── signals/                # 信号生成引擎
│   ├── trend_following.py  # 双均线交叉, MACD 信号
│   ├── mean_reversion.py   # RSI 超买超卖, 布林带回归
│   ├── multi_factor_scorer.py  # 多因子综合打分
│   └── filter_chain.py     # 信号过滤器链（波动率/趋势过滤）
│
├── portfolio/              # 仓位管理与风控
│   ├── fixed_sizing.py     # 固定比例仓位
│   ├── atr_sizing.py       # ATR 波动率动态仓位
│   ├── kelly_sizing.py     # 凯利公式仓位
│   ├── stop_loss.py        # 固定止损
│   ├── trailing_stop.py    # 移动止损（峰值回撤触发）
│   ├── daily_loss_limit.py # 日内亏损限制
│   └── risk_manager.py     # 可组合风控管理器
│
├── backtest/               # 回测引擎
│   ├── vectorbt_engine.py  # 向量化回测主引擎
│   ├── result.py           # 标准化回测结果 BacktestResult
│   ├── metrics.py          # Sharpe, Calmar, 最大回撤, 胜率等
│   └── slippage.py         # 滑点 + 佣金/印花税模型
│
├── optimization/           # 参数优化
│   ├── grid_search.py      # 网格搜索（多参数组合遍历）
│   ├── sensitivity.py      # 参数敏感性分析
│   └── overfitting.py      # 过拟合检测（样本内外对比）
│
├── prediction/             # AI 价格预测（ML 模块）
│   ├── base.py             # 抽象预测器基类
│   ├── features.py         # 特征工程（技术指标→特征矩阵）
│   ├── models.py           # 多个 ML 模型（回归/分类）
│   ├── ensemble.py         # 集成学习器
│   └── evaluation.py       # 预测评估指标
│
├── agent/                  # AI Agent 智能分析
│   ├── quant_agent.py      # 量化 Agent 统一入口（全流程编排）
│   ├── chat_agent.py       # 对话 Agent（自然语言交互，本地规则引擎）
│   ├── market_regime.py    # 市场状态诊断（趋势/震荡/高波动）
│   ├── strategy_selector.py  # 策略自动选择与推荐
│   ├── auto_optimizer.py   # 参数自动优化器
│   └── report_generator.py # 综合报告生成
│
├── visualization/          # 可视化
│   ├── equity_curve.py     # 权益曲线
│   ├── drawdown.py         # 回撤曲线
│   ├── trades.py           # 买卖点标记
│   ├── pnl_histogram.py    # 盈亏分布直方图
│   ├── signal_scatter.py   # 信号散点图
│   └── dashboard.py        # 综合看板
│
├── live/                   # 实盘接口（框架预留）
├── utils/                  # 工具函数
├── examples/               # 示例脚本
├── tests/                  # 单元测试
│
├── requirements.txt        # 依赖清单
└── pyproject.toml          # 项目元数据
```

## 核心特性

### 1. 数据层
- **统一 Schema**：AKShare / yfinance / baostock 多数据源自动映射为标准 OHLCV 列名
- **本地缓存**：Parquet 格式缓存，支持 TTL 过期策略，减少重复请求
- **前复权/后复权**：通过 AKShare 的 `qfq`/`hfq` 参数自动处理

### 2. 因子库（可扩展注册中心）
```python
from factors.base import Factor
from factors.registry import FactorRegistry

@FactorRegistry.register          # 装饰器注册，热插拔
class MyFactor(Factor):
    def compute(self, data):
        return data["close"].pct_change(20)
```
- 内置 10+ 技术因子：SMA, EMA, MACD, RSI, BOLL, ATR, ROC, Momentum, 波动率
- 注册中心支持按名称动态创建因子实例

### 3. 信号引擎
- **趋势跟踪**：双均线交叉、MACD 金叉死叉
- **均值回归**：RSI 超买超卖、布林带突破
- **多因子打分**：多因子加权综合评分，信号过滤器链（波动率过滤 + 趋势过滤）

### 4. 仓位与风控
- **三种仓位模型**：固定比例 / ATR 动态 / 凯利公式
- **可组合风控**：`FixedStopLoss + TrailingStop + DailyLossLimit` 自由组合
- **A 股交易成本**：佣金万三（最低 5 元）+ 印花税千一（卖出单向）

### 5. 回测引擎
- **向量化回测**：逐日模拟信号执行，含滑点和交易成本
- **标准化输出**：统一的 `BacktestResult` 对象，Sharpe / Calmar / 最大回撤 / 胜率 / 盈亏比
- **Dashboard 可视化**：权益曲线 + 回撤曲线 + 买卖点标记 + 盈亏分布

### 6. AI Agent（本地规则引擎，无需 LLM API）
- **市场状态诊断**：自动识别趋势市/震荡市/高波动市
- **策略自动推荐**：根据市场状态选择最优策略类型
- **对话式交互**：支持中文自然语言查询（"帮我分析 000001"）
- **参数自动优化**：内置网格搜索，自动寻找最优参数组合
- **AI 价格预测**：ML 模型集成预测，含特征工程和评估

### 7. 参数优化
- **网格搜索**：多参数组合遍历，寻找最优 Sharpe / Calmar
- **敏感性分析**：单参数变化对策略表现的影响
- **过拟合检测**：样本内 vs 样本外对比，检测参数过拟合

## 关键可调参数

| 模块 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| 双均线 | fast_window / slow_window | 5 / 20 | 快慢线周期 |
| MACD | fast / slow / signal | 12 / 26 / 9 | 标准 MACD 参数 |
| RSI | window / oversold / overbought | 14 / 30 / 70 | 超买超卖阈值 |
| 布林带 | window / num_std | 20 / 2.0 | 窗口和标准差倍数 |
| 固定仓位 | fraction | 0.10 | 每次交易资金占比 |
| ATR 仓位 | risk_pct | 0.02 | 单笔风险比例 |
| 凯利仓位 | fraction | 0.25 | 分数凯利系数 |
| 止损 | stop_loss_pct | 0.07 | 固定止损 7% |
| 移动止损 | trailing_pct | 0.15 | 从峰值回撤 15% |
| 日内限制 | max_daily_loss_pct | 0.03 | 单日最大亏损 3% |
| 回测 | initial_capital / commission / slippage | 100万 / 万3 / 千1 | 初始资金与成本 |

## 已知局限与改进方向

1. **趋势策略**：震荡市中频繁假信号 → 建议添加波动率过滤器降低交易频率
2. **参数敏感性**：单周期均线参数过度敏感 → 使用多周期组合降低过拟合
3. **因子共线性**：多因子打分时因子间可能高度相关 → 正交化或 PCA 降维
4. **过拟合风险**：网格搜索最优参数可能过拟合历史 → 必须做样本外验证
5. **前视偏差**：信号计算必须严格使用 `shift()` 对齐 → 已通过向量化引擎规避
6. **实盘支持**：实盘接口仅做框架预留 → 需接入券商 API（如 XTP/QMT）

## 技术栈

- **语言**：Python 3.10+
- **数据源**：AKShare, yfinance, baostock
- **Web UI**：Streamlit
- **数据处理**：pandas, numpy
- **统计/ML**：scipy, statsmodels, scikit-learn
- **可视化**：matplotlib, seaborn
- **缓存**：pyarrow (Parquet)
- **报告**：python-pptx

## License

MIT
