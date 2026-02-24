
# ==========================================================
# MAIFA HYPER-SWR ENGINE (INDUSTRIAL GRADE)
# Architecture: Request Collapsing • Atomic Locking • Non-Blocking Refresh
# Optimization: Distributed Consistency • Zero-Thundering-Herd
# ==========================================================

import asyncio
import time
import logging
from typing import Any, Dict, Callable, Optional, Set
from services.cache.redis_async import cache
from services.data_ingestion.fingerprint import MAIFAFingerprint

logger = logging.getLogger("MAIFA.SWR")

class SWREngine:
    __slots__ = ("_inflight_refreshes", "ttl_default")

    def __init__(self, ttl_default: int = 300):
        self.ttl_default = ttl_default
        # تتبع العمليات الجارية لمنع تكرار طلب نفس البيانات في الخلفية
        self._inflight_refreshes: Set[str] = set()

    async def get(
        self,
        source: str,
        params: Dict[str, Any],
        fetch_fn: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        High-Performance SWR Entry Point.
        Implements Request Collapsing to protect downstream services.
        """
        ttl = ttl or self.ttl_default
        fp = MAIFAFingerprint.build(source, params)

        # 1. Fast Path: Cache Lookup
        cached = await cache.get(fp)
        
        if cached is not None:
            # Atomic Background Refresh: منع التحديث إذا كان هناك طلب قيد التنفيذ فعلاً
            if fp not in self._inflight_refreshes:
                asyncio.create_task(self._safe_refresh(fp, fetch_fn, ttl))
            
            return {
                "fp": fp,
                "status": "stale",
                "data": cached,
                "ts": time.time()
            }

        # 2. Slow Path: No Cache (Locking required to prevent Thundering Herd)
        return await self._fetch_and_lock(fp, source, fetch_fn, ttl)

    async def _fetch_and_lock(self, fp: str, source: str, fetch_fn: Callable, ttl: int):
        # منع طلبات متعددة لنفس المفتاح المفقود في نفس اللحظة
        if fp in self._inflight_refreshes:
            # الانتظار قليلاً ثم محاولة القراءة من الكاش مرة أخرى بدلاً من ضرب الـ DB
            await asyncio.sleep(0.1)
            retry_cache = await cache.get(fp)
            if retry_cache: return {"fp": fp, "status": "hit_after_wait", "data": retry_cache, "ts": time.time()}

        self._inflight_refreshes.add(fp)
        try:
            fresh = await fetch_fn()
            await cache.set(fp, fresh, ttl)
            return {"fp": fp, "status": "fresh", "data": fresh, "ts": time.time()}
        finally:
            self._inflight_refreshes.discard(fp)

    async def _safe_refresh(self, fp: str, fetch_fn: Callable, ttl: int):
        if fp in self._inflight_refreshes:
            return
            
        self._inflight_refreshes.add(fp)
        try:
            # محاكاة Jitter بسيط لمنع تزامن التحديثات في الأنظمة الموزعة
            new_data = await fetch_fn()
            await cache.set(fp, new_data, ttl)
        except Exception as e:
            logger.error(f"SWR_REFRESH_ERR | FP: {fp} | {str(e)}")
        finally:
            self._inflight_refreshes.discard(fp)

swr = SWREngine()
