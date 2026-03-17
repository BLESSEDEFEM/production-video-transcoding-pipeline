"""Test Redis queue"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.queue.transcoding_queue import enqueue_transcoding_job, get_job_status
import time

print("="*70)
print("TESTING REDIS QUEUE")
print("="*70)

# Test with existing video
video_id = 1  # Change to your video ID
qualities = ['360p', '720p']

print(f"\nQueueing jobs for video {video_id}...\n")

job_ids = []
for quality in qualities:
    job_id = enqueue_transcoding_job(video_id, quality)
    job_ids.append(job_id)
    print(f"✅ Queued {quality}: {job_id}")

print(f"\n📊 Checking job statuses...\n")

for job_id in job_ids:
    status = get_job_status(job_id)
    print(f"Job {job_id[:8]}...: {status.get('status', 'unknown')}")

print("\n✅ Queue test complete!")
print("Jobs are queued but won't process until worker is started")