import time
import logging
from functools import wraps
from typing import Callable, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState

logger = logging.getLogger("orca.reliability")

def is_transient_error(exception: BaseException) -> bool:
    """Determine if the exception is a retryable transient failure."""
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True
    
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        if status >= 500:
            return True
        if status == 429:  # Rate limited (usually transient)
            return True
        return False
        
    # Fallback heuristic for standard Python Connection/Timeout errors if httpx is not the only client
    err_str = str(exception).lower()
    if any(x in err_str for x in ["timeout", "connection refused", "connection reset", "broken pipe", "read timed out"]):
        return True

    return False

def retry_if_transient(retry_state: RetryCallState) -> bool:
    """Tenacity condition to trigger a retry."""
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        return is_transient_error(exception)
    return False

def on_retry_error(retry_state: RetryCallState):
    """Callback to log intermediate retry attempts."""
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    fn_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    
    logger.warning(
        f"Provider Retry | method={fn_name} | attempt={attempt} | "
        f"error={exception.__class__.__name__} | msg={str(exception)}"
    )

def with_reliability(provider_name: str, max_retries: int = 2):
    """
    Decorator for wrapping provider HTTP calls with tenacity retries and graceful None fallback.
    """
    def decorator(func: Callable):
        
        # We use tenacity to handle the retry logic transparently
        tenacity_decorator = retry(
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=3.0),
            retry=retry_if_transient,
            after=on_retry_error,
            reraise=True
        )
        
        # Apply tenacity to the inner function
        retriable_func = tenacity_decorator(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                # Execute the tenacity-wrapped function
                return retriable_func(*args, **kwargs)
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                is_transient = is_transient_error(e)
                
                logger.error(
                    f"Provider Final Failure | "
                    f"provider={provider_name} | "
                    f"method={func.__name__} | "
                    f"error={e.__class__.__name__} | "
                    f"transient={is_transient} | "
                    f"elapsed_s={elapsed:.3f}"
                )
                
                # Graceful degradation - fall back to None
                return None
                
        return wrapper
    return decorator
