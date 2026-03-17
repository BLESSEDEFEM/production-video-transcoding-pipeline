"""
Prometheus metrics for the video transcoding pipeline.

Think of each metric as a counter or gauge on a dashboard:
- Counter: only goes UP (like an odometer — total jobs processed)
- Gauge:   goes UP and DOWN (like a speedometer — current queue depth)
- Histogram: measures distributions (like how long jobs take — most are 30s, some are 5min)
"""
from prometheus_client import Counter, Gauge, Histogram, Summary

# ─────────────────────────────────────────────────────────────────
# COUNTERS (only go up — track totals)
# ─────────────────────────────────────────────────────────────────

# Total videos uploaded since server started
# labels=["status"] means we can track by status:
#   videos_uploaded_total{status="approved"} 40
#   videos_uploaded_total{status="rejected"} 7
videos_uploaded_total = Counter(
    'videos_uploaded_total',
    'Total number of videos uploaded',
    ['status']   # label: "approved", "rejected", "failed"
)

# Total transcoding jobs
# labels=["quality", "status"] means we track each quality level separately:
#   jobs_total{quality="720p", status="completed"} 15
#   jobs_total{quality="360p", status="failed"} 2
jobs_total = Counter(
    'transcoding_jobs_total',
    'Total transcoding jobs processed',
    ['quality', 'status']   # labels: quality="720p", status="completed"
)

# Total emails sent
emails_sent_total = Counter(
    'emails_sent_total',
    'Total notification emails sent',
    ['type']   # label: "success", "failure"
)

# ─────────────────────────────────────────────────────────────────
# GAUGES (go up AND down — current state right now)
# ─────────────────────────────────────────────────────────────────

# How many jobs are currently waiting in Redis queue?
# When a job is added: queue_depth.inc()   (+1)
# When a job is picked up by worker: queue_depth.dec()  (-1)
queue_depth = Gauge(
    'transcoding_queue_depth',
    'Number of jobs currently waiting in the Redis queue'
)

# How many workers are currently active?
active_workers = Gauge(
    'active_workers',
    'Number of active transcoding workers'
)

# How many jobs are currently running right now?
jobs_in_progress = Gauge(
    'jobs_in_progress',
    'Number of transcoding jobs currently processing'
)

# ─────────────────────────────────────────────────────────────────
# HISTOGRAMS (measure time distributions)
# ─────────────────────────────────────────────────────────────────

# How long do transcoding jobs take?
# Histogram stores counts in "buckets":
#   jobs under 30s:  X times
#   jobs under 60s:  Y times
#   jobs under 5min: Z times
#   etc.
# This lets Grafana draw a distribution chart
job_duration_seconds = Histogram(
    'transcoding_job_duration_seconds',
    'Time spent processing a transcoding job',
    ['quality'],   # label: which quality was being transcoded
    buckets=[30, 60, 120, 300, 600, 1800, 3600]
    # buckets = the time thresholds (30s, 1min, 2min, 5min, 10min, 30min, 1hr)
)

# How long do video uploads take?
upload_duration_seconds = Histogram(
    'video_upload_duration_seconds',
    'Time spent handling a video upload',
    buckets=[1, 5, 10, 30, 60, 120]
)

# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def record_job_complete(quality: str, duration_seconds: float):
    """Call this when a job finishes successfully."""
    jobs_total.labels(quality=quality, status='completed').inc()
    job_duration_seconds.labels(quality=quality).observe(duration_seconds)
    jobs_in_progress.dec()

def record_job_failed(quality: str):
    """Call this when a job fails."""
    jobs_total.labels(quality=quality, status='failed').inc()
    jobs_in_progress.dec()

def record_job_started(quality: str):
    """Call this when a job starts."""
    jobs_in_progress.inc()

def record_video_upload(status: str):
    """Call this when a video is uploaded and inspected."""
    videos_uploaded_total.labels(status=status).inc()