import time
from functools import wraps
from server.cache import redis_client
from server.settings import config
from fastapi import HTTPException

def check_circuit_breaker(api_name: str):
    """
    Check if an external API (like OpenAI) is currently open (failing).
    If it failed threshold times in the last window, block it.
    """
    fails_key = f"circuit_breaker:fails:{api_name}"
    last_fail_key = f"circuit_breaker:last_fail:{api_name}"

    try:
        fails = int(redis_client.get(fails_key) or 0)
        
        if fails >= config.API_FAILURE_THRESHOLD:
            last_fail = float(redis_client.get(last_fail_key) or 0)
            if (time.time() - last_fail) < config.API_RECOVERY_TIMEOUT_SEC:
                # Circuit is OPEN - don't hit the API
                raise HTTPException(
                    status_code=503, 
                    detail=f"Service {api_name} is currently degraded. Please try again later."
                )
            else:
                # Half-Open state: let one through
                pass
    except Exception as e:
        if isinstance(e, HTTPException): raise e
        # Fail closed internally if redis fails

def record_api_failure(api_name: str):
    """Log failures into the circuit breaker."""
    try:
        fails_key = f"circuit_breaker:fails:{api_name}"
        last_fail_key = f"circuit_breaker:last_fail:{api_name}"
        
        redis_client.incr(fails_key)
        redis_client.set(last_fail_key, time.time())
        # Clear failures after the timeout window x 2
        redis_client.expire(fails_key, config.API_RECOVERY_TIMEOUT_SEC * 2)
    except Exception:
        pass

def record_api_success(api_name: str):
    """Close the circuit on success."""
    try:
        fails_key = f"circuit_breaker:fails:{api_name}"
        redis_client.delete(fails_key)
    except Exception:
        pass

def with_circuit_breaker(api_name: str):
    """Decorator to securely wrap external API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            check_circuit_breaker(api_name)
            try:
                result = func(*args, **kwargs)
                record_api_success(api_name)
                return result
            except Exception as e:
                # Track failure before raising back to handler
                record_api_failure(api_name)
                raise e
        return wrapper
    return decorator
