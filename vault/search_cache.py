"""Search result cache helpers for VaultSearch."""

from __future__ import annotations

from typing import Optional

from .semantic import provider_dimension, provider_id


class SearchCacheMixin:
        def set_cache_config(
            self,
            enabled: Optional[bool] = None,
            max_size: Optional[int] = None,
            ttl_seconds: Optional[int] = None,
            max_memory_mb: Optional[float] = None,
        ) -> None:
            """
            配置搜尋結果快取。

            Args:
                enabled: 是否啟用快取（None 表示不改變）
                max_size: 最大快取條目數（None 表示不改變）
                ttl_seconds: 快取有效期（秒，None 表示不改變）
                max_memory_mb: 最大快取內存使用量（MB，None 表示不改變）
            """
            if enabled is not None:
                self._enable_cache = enabled
            if max_size is not None:
                self._cache_size = max(max_size, 1)
                # 如果縮小了快取大小，清理多餘的條目
                if len(self._cache) > self._cache_size:
                    self._evict_oldest(len(self._cache) - self._cache_size)
            if ttl_seconds is not None:
                self._cache_ttl = max(ttl_seconds, 1)
            if max_memory_mb is not None:
                self._max_cache_memory_mb = max(max_memory_mb, 0.1)
                # 如果超出內存限制，驅逐舊條目直到符合限制
                self._evict_to_memory_limit()

        def clear_cache(self) -> None:
            """清空所有快取。"""
            self._cache.clear()
            self._current_cache_memory = 0
            self._cache_hits = 0
            self._cache_misses = 0

        def get_cache_stats(self) -> dict:
            """取得快取統計資訊。"""
            total = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total * 100) if total > 0 else 0.0
            return {
                "enabled": self._enable_cache,
                "size": len(self._cache),
                "max_size": self._cache_size,
                "ttl_seconds": self._cache_ttl,
                "memory_usage_mb": round(self._current_cache_memory / (1024 * 1024), 2),
                "max_memory_mb": self._max_cache_memory_mb,
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate_percent": round(hit_rate, 1),
            }

        def _get_cache_key(self, query: str, **kwargs) -> str:
            """生成快取鍵值。使用 JSON 序列化 + MD5 哈希，徹底避免鍵值衝突。"""
            import hashlib
            import json

            key_data = {"query": query, "params": kwargs}
            # sort_keys=True 確保參數順序不影響鍵值
            key_json = json.dumps(key_data, sort_keys=True, default=str)
            return hashlib.md5(key_json.encode("utf-8")).hexdigest()

        def _embed_cache_identity(self) -> dict:
            """Return provider identity fields that affect semantic/vector result caches."""
            provider = self._embed
            if provider is None:
                return {"provider_id": "", "dimension": ""}
            try:
                pid = provider_id(provider)
            except Exception:
                pid = str(getattr(provider, "provider_id", provider.__class__.__name__))
            try:
                dim = provider_dimension(provider)
            except Exception:
                dim = str(getattr(provider, "dim", ""))
            return {"provider_id": pid, "dimension": dim}

        def _get_from_cache(self, cache_key: str) -> Optional[list[dict]]:
            """從快取取得結果，過期則返回 None。"""
            if not self._enable_cache:
                return None

            import time
            entry = self._cache.get(cache_key)
            if entry is None:
                self._cache_misses += 1
                return None

            timestamp, results, size_bytes = entry
            # 檢查是否過期
            if time.time() - timestamp > self._cache_ttl:
                del self._cache[cache_key]
                self._current_cache_memory -= size_bytes
                self._cache_misses += 1
                return None

            self._cache_hits += 1
            # 返回深拷貝，避免外部修改影響快取
            return [dict(r) for r in results]

        def _estimate_result_size(self, results: list[dict]) -> int:
            """估算快取結果的內存大小（字節）。"""
            import sys
            total = 0
            for r in results:
                total += sys.getsizeof(r)
                for k, v in r.items():
                    total += sys.getsizeof(k) + sys.getsizeof(v)
            return total

        def _set_to_cache(self, cache_key: str, results: list[dict]) -> None:
            """將結果存入快取。"""
            if not self._enable_cache:
                return

            import time
            # 估算大小
            size_bytes = self._estimate_result_size(results)
            max_bytes = int(self._max_cache_memory_mb * 1024 * 1024)

            # 如果單條結果就超過內存限制，直接跳過
            if size_bytes > max_bytes:
                return

            # 如果已存在，先扣除舊大小
            if cache_key in self._cache:
                old_size = self._cache[cache_key][2]
                self._current_cache_memory -= old_size

            # 快取條目數檢查
            if len(self._cache) >= self._cache_size and cache_key not in self._cache:
                self._evict_oldest(1)

            # 內存限制檢查
            self._evict_to_memory_limit()

            # 存儲深拷貝
            self._cache[cache_key] = (time.time(), [dict(r) for r in results], size_bytes)
            self._current_cache_memory += size_bytes

        def _evict_to_memory_limit(self) -> None:
            """驅逐舊快取條目直到內存使用量低於限制。"""
            max_bytes = int(self._max_cache_memory_mb * 1024 * 1024)
            if self._current_cache_memory <= max_bytes:
                return

            # 按時間排序，從最舊的開始驅逐
            items = sorted(self._cache.items(), key=lambda x: x[1][0])
            for key, (_, _, size_bytes) in items:
                if self._current_cache_memory <= max_bytes:
                    break
                del self._cache[key]
                self._current_cache_memory -= size_bytes

        def _evict_oldest(self, count: int) -> None:
            """驅逐最舊的快取條目。"""
            # 按時間排序，刪除最舊的
            items = sorted(self._cache.items(), key=lambda x: x[1][0])
            for i in range(min(count, len(items))):
                key = items[i][0]
                _, _, size_bytes = self._cache[key]
                self._current_cache_memory -= size_bytes
                del self._cache[key]
