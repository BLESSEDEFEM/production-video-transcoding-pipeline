"""
Admin API endpoints for the video transcoding pipeline.

These endpoints provide system-level visibility:
- Dashboard stats (totals, averages, health)
- All videos across all users
- All jobs with filtering by status
- System health (database, Redis, MinIO)

In production, these would be protected by an admin role check.
For now, they require any valid authentication token.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import redis
import os

from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.utils.dependencies import get_current_user, get_admin_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─────────────────────────────────────────────────────────────────
# DASHBOARD STATS — the big numbers at the top of the admin page
# ─────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_system_stats(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Returns high-level system statistics.
    
    This powers the top row of stat cards on the admin dashboard:
    total users, total videos, total jobs, success rate, etc.
    """
    # Count totals
    total_users = db.query(func.count(User.id)).scalar()
    total_videos = db.query(func.count(Video.id)).scalar()
    total_jobs = db.query(func.count(TranscodingJob.id)).scalar()
    
    # Count by status
    completed_jobs = db.query(func.count(TranscodingJob.id)).filter(
        TranscodingJob.status == "completed"
    ).scalar()
    
    failed_jobs = db.query(func.count(TranscodingJob.id)).filter(
        TranscodingJob.status == "failed"
    ).scalar()
    
    pending_jobs = db.query(func.count(TranscodingJob.id)).filter(
        TranscodingJob.status == "pending"
    ).scalar()
    
    processing_jobs = db.query(func.count(TranscodingJob.id)).filter(
        TranscodingJob.status == "processing"
    ).scalar()
    
    # Video statuses
    approved_videos = db.query(func.count(Video.id)).filter(
        Video.status == VideoStatus.APPROVED
    ).scalar()
    
    rejected_videos = db.query(func.count(Video.id)).filter(
        Video.status == VideoStatus.REJECTED
    ).scalar()
    
    completed_videos = db.query(func.count(Video.id)).filter(
        Video.status == VideoStatus.COMPLETED
    ).scalar()
    
    # Average processing time (only completed jobs)
    avg_time = db.query(func.avg(TranscodingJob.processing_time)).filter(
        TranscodingJob.status == "completed",
        TranscodingJob.processing_time.isnot(None)
    ).scalar()
    
    # Total storage used (sum of all transcoded file sizes)
    total_storage = db.query(func.sum(TranscodedVideo.file_size)).scalar() or 0
    
    # Total original storage
    total_original_storage = db.query(func.sum(Video.file_size)).scalar() or 0
    
    # Success rate
    success_rate = 0
    if total_jobs > 0:
        success_rate = round((completed_jobs / total_jobs) * 100, 1)
    
    return {
        "users": {
            "total": total_users
        },
        "videos": {
            "total": total_videos,
            "approved": approved_videos,
            "rejected": rejected_videos,
            "completed": completed_videos
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs,
            "pending": pending_jobs,
            "processing": processing_jobs,
            "success_rate": success_rate,
            "avg_processing_time": round(avg_time, 1) if avg_time else 0
        },
        "storage": {
            "originals_mb": round(total_original_storage / 1024 / 1024, 2),
            "transcoded_mb": round(total_storage / 1024 / 1024, 2),
            "total_mb": round((total_original_storage + total_storage) / 1024 / 1024, 2)
        }
    }


# ─────────────────────────────────────────────────────────────────
# ALL VIDEOS — see every video in the system
# ─────────────────────────────────────────────────────────────────

@router.get("/videos")
async def get_all_videos(
    status: Optional[str] = Query(None, description="Filter by status: uploaded, approved, rejected, completed, failed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Returns all videos across all users with pagination.
    
    Optional filter by status.
    Includes the owner's username for each video.
    """
    query = db.query(Video)
    
    # Apply status filter if provided
    if status:
        try:
            video_status = VideoStatus(status)
            query = query.filter(Video.status == video_status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}. Valid: uploaded, inspecting, approved, rejected, completed, failed")
    
    # Get total count (before pagination)
    total = query.count()
    
    # Apply pagination and ordering
    videos = query.order_by(Video.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for video in videos:
        # Get owner info
        owner = db.query(User).filter(User.id == video.user_id).first()
        
        # Get transcoded versions count
        transcoded_count = db.query(func.count(TranscodedVideo.id)).filter(
            TranscodedVideo.original_video_id == video.id
        ).scalar()
        
        # Get job count and status breakdown
        jobs = db.query(TranscodingJob).filter(
            TranscodingJob.video_id == video.id
        ).all()
        
        result.append({
            "id": video.id,
            "filename": video.filename,
            "owner": owner.username if owner else "Unknown",
            "owner_email": owner.email if owner else "Unknown",
            "status": video.status.value,
            "file_size_mb": round((video.file_size or 0) / 1024 / 1024, 2),
            "resolution": video.resolution or "Unknown",
            "codec": video.codec or "Unknown",
            "duration": video.duration or 0,
            "inspection_passed": video.inspection_passed,
            "rejection_reason": video.rejection_reason,
            "transcoded_versions": transcoded_count,
            "jobs_completed": sum(1 for j in jobs if j.status == "completed"),
            "jobs_failed": sum(1 for j in jobs if j.status == "failed"),
            "jobs_total": len(jobs),
            "created_at": video.created_at.isoformat() if video.created_at else None
        })
    
    return {
        "videos": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ─────────────────────────────────────────────────────────────────
# ALL JOBS — see every transcoding job
# ─────────────────────────────────────────────────────────────────

@router.get("/jobs")
async def get_all_jobs(
    status: Optional[str] = Query(None, description="Filter by status: pending, processing, completed, failed"),
    quality: Optional[str] = Query(None, description="Filter by quality: 360p, 480p, 720p, 1080p"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Returns all transcoding jobs with filtering and pagination.
    
    Includes the video filename and owner for context.
    """
    query = db.query(TranscodingJob)
    
    # Apply filters
    if status:
        query = query.filter(TranscodingJob.status == status)
    if quality:
        query = query.filter(TranscodingJob.quality == quality)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    jobs = query.order_by(TranscodingJob.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for job in jobs:
        # Get video info
        video = db.query(Video).filter(Video.id == job.video_id).first()
        owner = None
        if video:
            owner = db.query(User).filter(User.id == video.user_id).first()
        
        result.append({
            "id": job.id,
            "video_id": job.video_id,
            "filename": video.filename if video else "Unknown",
            "owner": owner.username if owner else "Unknown",
            "quality": job.quality,
            "status": job.status,
            "progress": job.progress,
            "verification_passed": job.verification_passed,
            "processing_time": round(job.processing_time, 1) if job.processing_time else None,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        })
    
    return {
        "jobs": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ─────────────────────────────────────────────────────────────────
# SYSTEM HEALTH — check if all services are reachable
# ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def get_system_health(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """
    Checks connectivity to all backend services.
    
    Returns status for: database, Redis, MinIO.
    Useful for debugging when something stops working.
    """
    health = {
        "database": {"status": "unknown"},
        "redis": {"status": "unknown"},
        "minio": {"status": "unknown"}
    }
    
    # Check database
    try:
        db.execute(func.now())
        health["database"] = {"status": "healthy"}
    except Exception as e:
        health["database"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Redis
    try:
        r = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True
        )
        r.ping()
        
        # Also get queue info
        queue_length = r.llen("rq:queue:transcoding")
        worker_count = len(r.smembers("rq:workers"))
        
        health["redis"] = {
            "status": "healthy",
            "queue_length": queue_length,
            "active_workers": worker_count
        }
    except Exception as e:
        health["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check MinIO
    try:
        from app.storage import minio_client
        bucket = os.getenv("MINIO_BUCKET", "videos")
        minio_client.bucket_exists(bucket)
        health["minio"] = {"status": "healthy", "bucket": bucket}
    except Exception as e:
        health["minio"] = {"status": "unhealthy", "error": str(e)}
    
    # Overall status
    all_healthy = all(
        s["status"] == "healthy" for s in health.values()
    )
    
    return {
        "overall": "healthy" if all_healthy else "degraded",
        "services": health
    }