import os
import json
import redis
from datetime import timedelta

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Initialize Production Redis Pool
_redis_pool = redis.ConnectionPool.from_url(REDIS_URL, max_connections=50, decode_responses=True)
redis_client = redis.Redis(connection_pool=_redis_pool)

def get(key, default=None):
    """Retrieve JSON-deserialized object from Redis"""
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else default
    except Exception as e:
        print(f"⚠️ Redis Get Error: {e}")
        return default

def set(key, value, ttl_seconds=3600):
    """Store JSON object in Redis with expiration"""
    try:
        val = json.dumps(value, ensure_ascii=False)
        redis_client.setex(key, timedelta(seconds=ttl_seconds), val)
        return True
    except Exception as e:
        print(f"⚠️ Redis Set Error: {e}")
        return False

def check_rate_limit(user_id: int, plan: str, resource: str) -> bool:
    """Enterprise Rate Limiting Strategy (Token Bucket/Counter per User Plan)"""
    limits = {
        'free': 10,
        'pro': 100,
        'enterprise': 1000
    }
    limit = limits.get(plan.lower(), 10)
    
    # Key strategy: rate_limit:crawls:user_123:minute
    import time
    current_minute = int(time.time() / 60)
    key = f"rate_limit:{resource}:user_{user_id}:{current_minute}"
    
    try:
        pipe = redis_client.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, 60) # reset window next minute
        results = pipe.execute()
        
        current_usage = results[0]
        return current_usage <= limit
    except Exception:
        return True # Fail open to avoid blocking users if Redis drops

def acquire_lock(lock_key: str, timeout: int = 10) -> bool:
    """Implement Idempotency and Job Deduplication using Redis Locks"""
    try:
        # returns True if set was successful (lock acquired), False if existing
        return bool(redis_client.set(lock_key, "locked", nx=True, ex=timeout))
    except Exception as e:
        return False
