"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。以下股票池仅为示例。
==================================================
股票池定义模块。
"""

# A股示例股票池（沪深300成分股子集）
A_SHARE_POOL: dict[str, str] = {
    "000001": "平安银行",
    "000002": "万科A",
    "000858": "五粮液",
    "002415": "海康威视",
    "300750": "宁德时代",
    "600036": "招商银行",
    "600276": "恒瑞医药",
    "600519": "贵州茅台",
    "600887": "伊利股份",
    "601318": "中国平安",
}

# 美股示例股票池
US_STOCK_POOL: dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corp.",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "NVDA": "NVIDIA Corp.",
    "TSLA": "Tesla Inc.",
}


def get_a_share_symbols() -> list[str]:
    """获取A股示例股票池代码列表。"""
    return list(A_SHARE_POOL.keys())


def get_us_symbols() -> list[str]:
    """获取美股示例股票池代码列表。"""
    return list(US_STOCK_POOL.keys())


def get_symbol_name(symbol: str) -> str:
    """根据代码获取股票名称。"""
    all_pools = {**A_SHARE_POOL, **US_STOCK_POOL}
    return all_pools.get(symbol, symbol)
