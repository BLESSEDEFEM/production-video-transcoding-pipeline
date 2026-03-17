"""
Redis client for RQ
"""
import redis
import os
from dotenv import load_dotenv

load_dotenv()

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

# For RQ (must NOT decode responses - RQ uses binary data)
rq_redis = redis.from_url(REDIS_URL, decode_responses=False)

# For app use (caching, pub/sub, etc. - string-friendly)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def test_connection():
    """Test Redis connection"""
    try:
        rq_redis.ping()
        print("✅ Redis connected")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()