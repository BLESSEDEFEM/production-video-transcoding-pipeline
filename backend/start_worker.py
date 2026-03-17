"""
Start RQ worker to process transcoding jobs
"""
import platform
from rq import SimpleWorker, Worker
from rq.timeouts import BaseDeathPenalty
from app.queue.redis_client import rq_redis
from app.queue.transcoding_queue import transcoding_queue


class DummyDeathPenalty(BaseDeathPenalty):
    """No-op timeout class for Windows (no SIGALRM)"""
    def setup_death_penalty(self):
        pass

    def cancel_death_penalty(self):
        pass


print("="*70)
print("🎬 STARTING TRANSCODING WORKER")
print("="*70)
print(f"Queue: {transcoding_queue.name}")
print(f"Redis: {rq_redis}")
print(f"OS: {platform.system()}")
print("="*70)
print(f"\nListening for jobs...(Ctrl+C to stop)\n")

if platform.system() == "Windows":
    # Windows: no fork, no SIGALRM
    worker = SimpleWorker(
        [transcoding_queue],
        connection=rq_redis,
    )
    worker.death_penalty_class = DummyDeathPenalty
    worker.work()
else:
    # Linux/Docker: full RQ with timeouts
    worker = Worker([transcoding_queue], connection=rq_redis)
    worker.work()