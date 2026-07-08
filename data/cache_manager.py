"""
==================================================
 风险提示：本文件为量化交易学习工具的一部分，
 不构成任何投资建议。
==================================================
数据缓存管理模块，使用 Parquet 格式本地缓存。
"""

import os
from datetime import datetime, timedelta

import pandas as pd


class CacheManager:
    """本地数据缓存管理器。

    两级缓存：内存 dict + 磁盘 Parquet 文件。
    支持 TTL 过期策略。

    使用方法:
        cache = CacheManager(cache_dir="./data/cache")
        cache.put("000001_daily", df)
        df = cache.get("000001_daily", ttl_days=1)
    """

    def __init__(self, cache_dir: str = "./data/cache"):
        self._cache_dir = cache_dir
        self._memory_cache: dict[str, pd.DataFrame] = {}
        self._timestamps: dict[str, datetime] = {}
        os.makedirs(cache_dir, exist_ok=True)

    def _key_to_path(self, key: str) -> str:
        """将缓存 key 映射为文件路径。"""
        safe_key = key.replace("/", "_").replace("\\", "_")
        return os.path.join(self._cache_dir, f"{safe_key}.parquet")

    def get(
        self, key: str, ttl_days: int | None = None
    ) -> pd.DataFrame | None:
        """获取缓存数据。

        Args:
            key: 缓存键。
            ttl_days: TTL 天数，None 表示永不过期。

        Returns:
            缓存命中时返回 DataFrame，否则 None。
        """
        # 先查内存
        if key in self._memory_cache:
            ts = self._timestamps.get(key)
            if ts and ttl_days is not None:
                if datetime.now() - ts > timedelta(days=ttl_days):
                    del self._memory_cache[key]
                    del self._timestamps[key]
                    return None
            return self._memory_cache[key].copy()

        # 再查磁盘
        filepath = self._key_to_path(key)
        if not os.path.exists(filepath):
            return None

        if ttl_days is not None:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if datetime.now() - mtime > timedelta(days=ttl_days):
                return None

        df = pd.read_parquet(filepath)
        self._memory_cache[key] = df
        self._timestamps[key] = datetime.now()
        return df.copy()

    def put(self, key: str, df: pd.DataFrame) -> None:
        """写入缓存。

        Args:
            key: 缓存键。
            df: 要缓存的 DataFrame。
        """
        self._memory_cache[key] = df.copy()
        self._timestamps[key] = datetime.now()

        filepath = self._key_to_path(key)
        df.to_parquet(filepath, index=True)

    def exists(self, key: str, ttl_days: int | None = None) -> bool:
        """检查缓存是否存在且有效。"""
        # 内存
        if key in self._memory_cache:
            if ttl_days is not None:
                ts = self._timestamps.get(key)
                if ts and datetime.now() - ts > timedelta(days=ttl_days):
                    return False
            return True

        # 磁盘
        filepath = self._key_to_path(key)
        if not os.path.exists(filepath):
            return False

        if ttl_days is not None:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if datetime.now() - mtime > timedelta(days=ttl_days):
                return False

        return True

    def clear(self, key: str | None = None) -> None:
        """清除缓存。

        Args:
            key: 指定 key 清除，None 清空全部。
        """
        if key:
            self._memory_cache.pop(key, None)
            self._timestamps.pop(key, None)
            filepath = self._key_to_path(key)
            if os.path.exists(filepath):
                os.remove(filepath)
        else:
            self._memory_cache.clear()
            self._timestamps.clear()
            for f in os.listdir(self._cache_dir):
                os.remove(os.path.join(self._cache_dir, f))
