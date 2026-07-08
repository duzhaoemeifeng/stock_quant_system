"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
日志配置模块。
"""

import logging
import sys


def setup_logger(
    name: str = "quant_system",
    level: int = logging.INFO,
    log_file: str | None = None,
) -> logging.Logger:
    """创建并配置 logger 实例。

    Args:
        name: logger 名称。
        level: 日志级别。
        log_file: 可选的日志文件路径。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


# 默认全局 logger
logger = setup_logger()
