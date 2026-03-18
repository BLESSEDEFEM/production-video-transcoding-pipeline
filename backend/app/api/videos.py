from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import io
import shutil
from pathlib import Path
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.api.auth import get_current_user
from app.storage import minio_client

# Use the adapter functions
from app.inspection.validator import validate_video_source
from app.inspection.fingerprint import generate_fingerprint

router = APIRouter(prefix="/api", tags=["videos"])

UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_appropriate_qualities(original_height: int) -> list:
    """
    Determine which qualities to transcode based on original resolution
    NEVER upscale - only same or lower quality
    """
    quality_heights = {
        '360p': 360,
        '480p': 480,
        '720p': 720,
        '1080p': 1080,
        '2160p': 2160
    }
    
    # Only include qualities <= original height
    appropriate = [
        quality for quality, height in quality_heights.items()
        if height <= original_height
    ]
    
    return appropriate if appropriate else ['360p']  # Minimum 360p


async def inspect_video_task(video_id: int, temp_path: str, db: Session):
    """
    Background task to inspect uploaded video
    Runs validation, fingerprinting, and updates database
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        
        # Update status
        video.status = VideoStatus.INSPECTING
        db.commit()
        
        # Run validation (uses your VideoValidator via adapter)
        validation_result = validate_video_source(temp_path)
        
        # Generate fingerprint (uses your VideoFingerprint via adapter)
        fingerprint_data = generate_fingerprint(temp_path)
        
        # Extract resolution info
        resolution = fingerprint_data.get('resolution', 'unknown')
        video.resolution = resolution
        video.codec = fingerprint_data.get('codec')
        video.fps = fingerprint_data.get('fps')
        video.duration = fingerprint_data.get('duration')
        
        # Update video record
        video.fingerprint_hash = fingerprint_data['signature_hash']
        video.fingerprint_data = fingerprint_data  # Store full dict as JSON
        video.inspection_report = validation_result  # Store full dict as JSON
        
        if validation_result['passed']:
            video.status = VideoStatus.APPROVED
            video.inspection_passed = True
            
            # Determine appropriate qualities (no upscaling)
            original_height = fingerprint_data.get('height', 720)
            qualities = get_appropriate_qualities(original_height)
            
            print(f"\n📋 Original resolution: {resolution} ({original_height}p)")
            print(f"📋 Will transcode to: {qualities}")
            print(f"📋 Queueing transcoding jobs for video {video_id}...")
            
            # Queue transcoding jobs
            from app.queue.transcoding_queue import enqueue_transcoding_job
            
            for quality in qualities:
                job_id = enqueue_transcoding_job(video_id, quality)
                print(f"   ✅ Queued {quality}: Job {job_id}")
                
            print(f"   Total: {len(qualities)} jobs queued\n")
            
            # Send email notification: video approved
            try:
                user = db.query(User).filter(User.id == video.user_id).first()
                if user:
                    from app.services.email_service import notify_upload_approved
                    notify_upload_approved(
                        to_email=user.email,
                        filename=video.filename,
                        video_id=video_id,
                        resolution=resolution,
                        qualities=qualities
                    )
            except Exception as e:
                print(f"⚠️  Email notification failed (non-fatal): {e}")
        else:
            video.status = VideoStatus.REJECTED
            video.inspection_passed = False
            video.rejection_reason = validation_result.get('summary', 'Validation failed')
            
            # Send email notification: video rejected
            try:
                user = db.query(User).filter(User.id == video.user_id).first()
                if user:
                    from app.services.email_service import notify_upload_rejected
                    notify_upload_rejected(
                        to_email=user.email,
                        filename=video.filename,
                        reason=video.rejection_reason
                    )
            except Exception as e:
                print(f"⚠️  Email notification failed (non-fatal): {e}")
         
        db.commit()
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    except Exception as e:
        print(f"Inspection failed: {str(e)}")
        if 'video' in locals():
            video.status = VideoStatus.FAILED
            video.rejection_reason = f"Inspection error: {str(e)}"
            db.commit()


@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload video file
    Saves to storage and queues for inspection
    """
    # Validate file type
    if not file.content_type.startswith('video/'):
        raise HTTPException(400, "File must be a video")
    
    # Check file size (limit to 2GB for now)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    if file_size > 2 * 1024 * 1024 * 1024:  # 2GB
        raise HTTPException(400, "File too large (max 2GB)")
    
    # Save to temporary location
    temp_path = UPLOAD_DIR / f"{current_user.id}_{datetime.now().timestamp()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Upload to MinIO
    object_name = f"originals/{current_user.id}/{file.filename}"
    try:
        minio_client.fput_object(
            bucket_name=os.getenv("MINIO_BUCKET"),
            object_name=object_name,
            file_path=str(temp_path),
            content_type=file.content_type
        )
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(500, f"Storage upload failed: {str(e)}")
    
    # Create database record
    video = Video(
        user_id=current_user.id,
        filename=file.filename,
        original_path=object_name,
        file_size=file_size,
        status=VideoStatus.UPLOADED
    )
    
    db.add(video)
    db.commit()
    db.refresh(video)

    # Queue inspection task (runs in background)
    background_tasks.add_task(
        inspect_video_task,
        video.id,
        str(temp_path),
        db
    )
    
    return {
        "id": video.id,
        "filename": video.filename,
        "file_size": video.file_size,
        "status": video.status.value,
        "message": "Video uploaded successfully. Inspection in progress."
    }


@router.get("/videos/{video_id}/inspection")
async def get_inspection_status(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get inspection status for a video
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(404, "Video not found")
    
    return {
        "video_id": video.id,
        "filename": video.filename,
        "status": video.status.value,
        "inspection_passed": video.inspection_passed,
        "inspection_report": video.inspection_report,
        "rejection_reason": video.rejection_reason,
        "fingerprint_hash": video.fingerprint_hash
    }


@router.get("/videos/{video_id}/summary")
async def get_video_summary(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get complete transcoding summary for user
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Get all transcoding jobs
    jobs = db.query(TranscodingJob).filter(
        TranscodingJob.video_id == video_id
    ).all()
    
    # Get all transcoded videos
    transcoded = db.query(TranscodedVideo).filter(
        TranscodedVideo.original_video_id == video_id
    ).all()
    
    # Calculate totals
    total_time = sum(j.processing_time for j in jobs if j.processing_time) or 0
    total_output_size = sum(t.file_size for t in transcoded) or 0
    
    return {
        "original": {
            "filename": video.filename,
            "resolution": video.resolution or "Unknown",
            "codec": video.codec or "Unknown",
            "fps": video.fps or 0,
            "duration": video.duration or 0,
            "file_size_mb": round((video.file_size or 0) / 1024 / 1024, 2),
            "bitrate_mbps": round((video.bitrate or 0) / 1000000, 2) if video.bitrate else 0,
            "inspection_passed": video.inspection_passed,
            "fingerprint": video.fingerprint_hash[:16] if video.fingerprint_hash else None
        },
        "transcoded": [
            {
                "quality": t.quality,
                "file_size_mb": round((t.file_size or 0) / 1024 / 1024, 2),
                "similarity_score": round(t.fingerprint_similarity or 0, 1),
                "verification_passed": next(
                    (j.verification_passed for j in jobs if j.quality == t.quality),
                    False
                ),
                "processing_time": round(
                    next((j.processing_time for j in jobs if j.quality == t.quality), 0),
                    1
                )
            }
            for t in transcoded
        ],
        "summary": {
            "total_qualities": len(transcoded),
            "total_processing_time": round(total_time, 1),
            "total_output_size_mb": round(total_output_size / 1024 / 1024, 2),
            "all_verified": all(j.verification_passed for j in jobs),
            "status": video.status.value
        }
    }
    
    
# List all user's videos   
@router.get("/videos/list")
async def list_user_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all videos for current user with transcoded versions"""
    
    videos = db.query(Video).filter(
        Video.user_id == current_user.id
    ).order_by(Video.created_at.desc()).all()
    
    result = []
    for video in videos:
        # Get transcoded versions
        transcoded = db.query(TranscodedVideo).filter(
            TranscodedVideo.original_video_id == video.id
        ).all()
        
        # Get jobs for processing times
        jobs = db.query(TranscodingJob).filter(
            TranscodingJob.video_id == video.id
        ).all()
        
        result.append({
            "id": video.id,
            "filename": video.filename,
            "resolution": video.resolution or "Unknown",
            "file_size_mb": round((video.file_size or 0) / 1024 / 1024, 2),
            "status": video.status.value,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "transcoded": [
                {
                    "quality": t.quality,
                    "file_size_mb": round((t.file_size or 0) / 1024 / 1024, 2),
                    "similarity_score": round(t.fingerprint_similarity or 0, 1),
                    "verification_passed": next(
                        (j.verification_passed for j in jobs if j.quality == t.quality),
                        False
                    ),
                    "processing_time": round(
                        next((j.processing_time for j in jobs if j.quality == t.quality), 0),
                        1
                    )
                }
                for t in transcoded
            ]
        })
    
    return result

# Download transcoded video
@router.get("/videos/{video_id}/download/{quality}")
async def download_transcoded_video(
    video_id: int,
    quality: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a specific transcoded version"""
    
    # Verify ownership
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Get transcoded video
    transcoded = db.query(TranscodedVideo).filter(
        TranscodedVideo.original_video_id == video_id,
        TranscodedVideo.quality == quality
    ).first()
    
    if not transcoded:
        raise HTTPException(404, f"Transcoded version {quality} not found")
    
    # Download from MinIO
    try:
        response = minio_client.get_object(
            bucket_name=os.getenv("MINIO_BUCKET"),
            object_name=transcoded.file_path
        )
        
        return StreamingResponse(
            response,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"attachment; filename={video.filename.replace('.mp4', '')}_{quality}.mp4"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"Download failed: {str(e)}")

# Delete video (with all transcoded versions)
@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete video and all associated data"""
    
    # Verify ownership
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(404, "Video not found")
    
    try:
        # Delete from MinIO - original
        try:
            minio_client.remove_object(
                bucket_name=os.getenv("MINIO_BUCKET"),
                object_name=video.original_path
            )
        except:
            pass  # Continue even if file doesn't exist
        
        # Delete transcoded files from MinIO
        transcoded_videos = db.query(TranscodedVideo).filter(
            TranscodedVideo.original_video_id == video_id
        ).all()
        
        for t in transcoded_videos:
            try:
                minio_client.remove_object(
                    bucket_name=os.getenv("MINIO_BUCKET"),
                    object_name=t.file_path
                )
            except:
                pass
        
        # Delete from database (cascade will handle related records)
        db.query(TranscodedVideo).filter(
            TranscodedVideo.original_video_id == video_id
        ).delete()
        
        db.query(TranscodingJob).filter(
            TranscodingJob.video_id == video_id
        ).delete()
        
        db.delete(video)
        db.commit()
        
        return {"message": "Video deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Delete failed: {str(e)}")

# Cancel ongoing transcoding
@router.post("/videos/{video_id}/cancel")
async def cancel_transcoding(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel all pending/processing transcoding jobs for a video"""
    
    # Verify ownership
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Update all pending/processing jobs to cancelled
    cancelled_count = db.query(TranscodingJob).filter(
        TranscodingJob.video_id == video_id,
        TranscodingJob.status.in_(['pending', 'processing'])
    ).update({
        "status": "cancelled",
        "error_message": "Cancelled by user"
    })
    
    db.commit()
    
    return {
        "message": f"Cancelled {cancelled_count} job(s)",
        "video_id": video_id
    }