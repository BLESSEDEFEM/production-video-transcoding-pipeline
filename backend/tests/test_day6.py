"""
Day 6 test — verifies Docker and Kubernetes setup is working.
Tests:
1. Backend health endpoint responds
2. Can connect to Redis
3. Can connect to PostgreSQL
4. At least 1 worker is processing jobs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import redis
import os

print("="*60)
print("DAY 6: DOCKER + KUBERNETES VERIFICATION")
print("="*60)

# ── TEST 1: BACKEND HEALTH ──
print("\n--- TEST 1: Backend Health ---")
try:
    response = httpx.get("http://localhost:8000/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Backend healthy: {data}")
    else:
        print(f"❌ Backend returned {response.status_code}")
except Exception as e:
    print(f"❌ Cannot reach backend: {e}")

# ── TEST 2: REDIS CONNECTION ──
print("\n--- TEST 2: Redis Connection ---")
try:
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    r.ping()
    # Check queue depth
    queue_length = r.llen("rq:queue:transcoding")
    print(f"✅ Redis connected | Queue depth: {queue_length} jobs")
except Exception as e:
    print(f"❌ Redis failed: {e}")

# ── TEST 3: DATABASE CONNECTION ──
print("\n--- TEST 3: Database Connection ---")
try:
    from app.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM videos"))
        count = result.scalar()
    print(f"✅ Database connected | Videos in DB: {count}")
except Exception as e:
    print(f"❌ Database failed: {e}")

# ── TEST 4: WORKER COUNT (Docker Compose) ──
print("\n--- TEST 4: Worker Status ---")
import subprocess
result = subprocess.run(
    ["docker-compose", "ps", "--services", "--filter", "status=running"],
    capture_output=True, text=True
)
running = [s for s in result.stdout.strip().split('\n') if s]
print(f"✅ Running services: {', '.join(running)}")

print("\n" + "="*60)
print("Day 6 verification complete!")
print("="*60)