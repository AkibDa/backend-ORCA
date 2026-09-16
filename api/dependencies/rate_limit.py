import time
import threading
from typing import Dict, List
import logging

from fastapi import Request, HTTPException, Depends
from backend.core.config import settings
from backend.api.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

class RateLimiter:
    """Thread-safe in-memory rate limiter using sliding windows."""
    
    def __init__(self):
        self._store: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._access_counter = 0

    def _sweep(self, now: float, window: int):
        """Remove expired keys to prevent memory growth. Must be called with lock held."""
        keys_to_delete = []
        for k, timestamps in self._store.items():
            valid_ts = [ts for ts in timestamps if now - ts <= window]
            if not valid_ts:
                keys_to_delete.append(k)
            else:
                self._store[k] = valid_ts
                
        for k in keys_to_delete:
            del self._store[k]

    def check_limit(self, key: str, limit: int, window: int):
        now = time.time()
        
        with self._lock:
            # Perform lazy memory cleanup periodically
            self._access_counter += 1
            if self._access_counter % 100 == 0:
                self._sweep(now, window)
                
            timestamps = self._store.get(key, [])
            timestamps = [ts for ts in timestamps if now - ts <= window]
            
            if len(timestamps) >= limit:
                self._store[key] = timestamps
                retry_after = int(window - (now - timestamps[0])) if timestamps else window
                
                logger.warning(f"Rate limit exceeded for {key}. Rejects with Retry-After: {retry_after}")
                raise HTTPException(
                    status_code=429, 
                    detail="Too many requests. Please try again shortly.",
                    headers={"Retry-After": str(retry_after)}
                )
                
            timestamps.append(now)
            self._store[key] = timestamps


# Singleton instances
_rate_limiter = RateLimiter()

_concurrency_lock = threading.Lock()
_active_requests = 0


def check_rate_limit(request: Request, user_id: str = Depends(get_current_user)) -> str:
    """Rate limit authenticated users based on their user_id."""
    key = f"user:{user_id}"
    _rate_limiter.check_limit(
        key=key, 
        limit=settings.ORCA_RATE_LIMIT_REQUESTS, 
        window=settings.ORCA_RATE_LIMIT_WINDOW_SECONDS
    )
    return user_id

def check_rate_limit_unauthenticated(request: Request) -> str:
    """Rate limit unauthenticated endpoints based on client IP."""
    ip = request.client.host if request.client else "127.0.0.1"
    key = f"ip:{ip}"
    _rate_limiter.check_limit(
        key=key, 
        limit=settings.ORCA_RATE_LIMIT_REQUESTS, 
        window=settings.ORCA_RATE_LIMIT_WINDOW_SECONDS
    )
    return ip

def acquire_concurrency_slot():
    """Concurrency dependency to limit simultaneous execution of expensive operations."""
    global _active_requests
    
    with _concurrency_lock:
        if _active_requests >= settings.ORCA_MAX_CONCURRENT_REQUESTS:
            logger.warning(f"Concurrency limit exceeded ({_active_requests}/{settings.ORCA_MAX_CONCURRENT_REQUESTS}). Rejecting request.")
            raise HTTPException(
                status_code=429, 
                detail="Too many requests. Please try again shortly."
            )
        _active_requests += 1
    
    try:
        # Yielding passes control to the endpoint logic
        yield
    finally:
        # Always runs, even if endpoint throws exception or client disconnects
        with _concurrency_lock:
            _active_requests -= 1
