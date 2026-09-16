import time
import logging
from functools import wraps
from typing import Callable, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState

try:
    from postgrest.exceptions import APIError
except ImportError:
    APIError = None

logger = logging.getLogger("orca.db_reliability")

def is_transient_db_error(exception: BaseException) -> bool:
    """Determine if the exception is a retryable transient failure for the database."""
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True
    
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        if status >= 500 or status == 429:
            return True
        return False
        
    if APIError and isinstance(exception, APIError):
        # postgrest-py APIError usually has a dictionary inside exception.args[0]
        try:
            err_dict = exception.args[0]
            if isinstance(err_dict, dict):
                # Check for standard PostgreSQL connection/timeout error codes or HTTP 5xx indicators
                # Class 08 — Connection Exception
                # Class 53 — Insufficient Resources (e.g. 53300 too many connections)
                code = err_dict.get("code")
                message = str(err_dict.get("message", "")).lower()
                
                if code and (str(code).startswith("08") or str(code).startswith("53")):
                    return True
                
                if "timeout" in message or "connection" in message or "500" in message or "502" in message or "503" in message or "504" in message:
                    return True
                    
        except Exception:
            pass
            
    # Fallback heuristic for standard Python Connection/Timeout errors
    err_str = str(exception).lower()
    if any(x in err_str for x in ["timeout", "connection refused", "connection reset", "broken pipe", "read timed out"]):
        return True

    return False

def retry_if_transient_db(retry_state: RetryCallState) -> bool:
    """Tenacity condition to trigger a DB retry."""
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        return is_transient_db_error(exception)
    return False

def on_retry_db_error(retry_state: RetryCallState):
    """Callback to log intermediate DB retry attempts."""
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    fn_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    
    logger.warning(
        f"DB Retry | method={fn_name} | attempt={attempt} | "
        f"error={exception.__class__.__name__} | msg={str(exception)}"
    )

_circuit_breaker_trip_time = 0.0
CIRCUIT_BREAKER_COOLDOWN_S = 60.0

def with_db_reliability(max_retries: int = 2):
    """
    Decorator for wrapping database calls with tenacity retries and graceful empty list fallback.
    """
    def decorator(func: Callable):
        
        tenacity_decorator = retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=0.25, min=0.25, max=1.0),
            retry=retry_if_transient_db,
            after=on_retry_db_error,
            reraise=True
        )
        
        retriable_func = tenacity_decorator(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _circuit_breaker_trip_time
            now = time.perf_counter()
            if _circuit_breaker_trip_time > 0 and (now - _circuit_breaker_trip_time) < CIRCUIT_BREAKER_COOLDOWN_S:
                if func.__name__ == 'get_location_by_id':
                    return None
                elif func.__name__.startswith('upsert_'):
                    return None
                return []

            start_time = time.perf_counter()
            try:
                result = retriable_func(*args, **kwargs)
                if _circuit_breaker_trip_time > 0:
                    _circuit_breaker_trip_time = 0.0  # Reset breaker on success
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                is_transient = is_transient_db_error(e)
                
                if not is_transient:
                    _circuit_breaker_trip_time = time.perf_counter()
                
                logger.error(
                    f"DB Final Failure | "
                    f"method={func.__name__} | "
                    f"error={e.__class__.__name__} | "
                    f"transient={is_transient} | "
                    f"elapsed_s={elapsed:.3f}"
                )
                
                # Graceful degradation - fall back to empty list (which most DB reads expect)
                if func.__name__ == 'get_location_by_id':
                    return None
                elif func.__name__.startswith('upsert_'):
                    return None
                return []
                
        return wrapper
    return decorator
