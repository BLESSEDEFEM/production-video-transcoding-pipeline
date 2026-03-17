"""
Transcoding job queue using Redis Queue (RQ)
"""
from rq import Queue
from app.queue.redis_client import rq_redis

# Create queue for transcoding jobs
transcoding_queue = Queue('transcoding', connection=rq_redis)

def enqueue_transcoding_job(video_id: int, quality: str) -> str:
    """
    Add transcoding job to queue
    
    Args:
        video_id: Video database ID
        quality: Target quality (360p, 480p, 720p, 1080p)
        
    Returns:
        Job ID (string)
    """
    from app.workers.chunked_transcoder import transcode_video_chunked_sync
    
    job = transcoding_queue.enqueue(
        transcode_video_chunked_sync,
        video_id=video_id,
        quality=quality,
        job_timeout='1h'
    )
    
    print(f"📋 Job queued: {job.id} (Video {video_id} → {quality})")
    
    return job.id

def get_job_status(job_id: str) -> dict:
    """Get status of a queued job"""
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=rq_redis)
        
        return {
            'job_id': job.id,
            'status': job.get_status(),
            'result': job.result,
            'exc_info': job.exc_info
        }
    except Exception as e:
        return {'error': str(e)}