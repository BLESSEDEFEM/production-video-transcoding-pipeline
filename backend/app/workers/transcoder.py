"""
Transcoding worker
Processes videos from Redis queue
"""
import subprocess
import json
import redis
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.inspection.fingerprint import generate_fingerprint, compare_fingerprints
from app.storage import minio_client
import os

# ═══════════════════════════════════════════════════════════
# NEW: Import Prometheus metrics
# ═══════════════════════════════════════════════════════════
from app.metrics import (
    record_job_started,
    record_job_complete,
    record_job_failed
)


# Quality presets
QUALITY_PRESETS = {
    '360p': {
        'resolution': '640x360',
        'bitrate': '800k',
        'audio_bitrate': '96k'
    },
    '480p': {
        'resolution': '854x480',
        'bitrate': '1400k',
        'audio_bitrate': '128k'
    },
    '720p': {
        'resolution': '1280x720',
        'bitrate': '2800k',
        'audio_bitrate': '128k'
    },
    '1080p': {
        'resolution': '1920x1080',
        'bitrate': '5000k',
        'audio_bitrate': '192k'
    }
}


def _send_progress(video_id: int, message: dict):
    """Send progress update via Redis pub/sub"""
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        redis_client.publish(
            f'progress_{video_id}',
            json.dumps(message)
        )
    except Exception as e:
        print(f"⚠️  Failed to send progress: {e}")


def transcode_video(video_id: int, quality: str):
    """
    Main transcoding function
    Called by RQ worker
    
    Args:
        video_id: Video database ID
        quality: Target quality (360p, 480p, 720p, 1080p)
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*70}")
        print(f"🎬 TRANSCODING JOB STARTED")
        print(f"{'='*70}")
        print(f"   Video ID: {video_id}")
        print(f"   Quality: {quality}")
        print(f"   Started: {datetime.now(timezone.utc)}")
        
        _send_progress(video_id, {
            'type': 'job_started',
            'quality': quality,
            'status': f'Starting {quality} transcoding...'
        })
        
        # Get video from database
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        # Create transcoding job record
        job = TranscodingJob(
            video_id=video_id,
            quality=quality,
            status='processing',
            started_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # ═══════════════════════════════════════════════════════════
        # NEW: Record job started in Prometheus
        # ═══════════════════════════════════════════════════════════
        record_job_started(quality)
        started_time = datetime.now(timezone.utc)
        
        # Download original from MinIO
        print(f"\n📥 Downloading original video...")
        _send_progress(video_id, {
            'type': 'download',
            'quality': quality,
            'status': 'Downloading original video...'
        })
        
        original_path = Path("temp_transcoding") / f"original_{video_id}.mp4"
        original_path.parent.mkdir(parents=True, exist_ok=True)
        
        minio_client.fget_object(
            bucket_name=os.getenv("MINIO_BUCKET"),
            object_name=video.original_path,
            file_path=str(original_path)
        )
        print(f"   ✅ Downloaded: {original_path}")
        
        # Generate original fingerprint
        print(f"\n🔍 Generating original fingerprint...")
        _send_progress(video_id, {
            'type': 'fingerprint',
            'quality': quality,
            'status': 'Generating fingerprint...'
        })
        
        original_fp = generate_fingerprint(str(original_path))
        print(f"   ✅ fingerprint: {original_fp['signature_hash'][:16]}...")
        
        # Transcode
        print(f"\n⚙️  Transcoding to {quality}...")
        _send_progress(video_id, {
            'type': 'transcoding',
            'quality': quality,
            'progress': 50,
            'status': f'Transcoding to {quality}...'
        })
        
        output_path = Path("temp_transcoding") / f"{video_id}_{quality}.mp4"
        
        success = _run_ffmpeg_transcode(
            str(original_path),
            str(output_path),
            quality
        )
        
        if not success:
            raise Exception("FFmpeg transcoding failed")
        
        print(f"   ✅ Transcoded: {output_path}")
        
        # Generate transcoded fingerprint
        print(f"\n🔍 Generating transcoded fingerprint...")
        _send_progress(video_id, {
            'type': 'fingerprint',
            'quality': quality,
            'progress': 75,
            'status': 'Verifying quality...'
        })
        
        transcoded_fp = generate_fingerprint(str(output_path))
        print(f"   ✅ Fingerprint: {transcoded_fp['signature_hash'][:16]}...")
        
        # Verify quality
        print(f"\n✅ Verifying quality...")
        verification = compare_fingerprints(original_fp, transcoded_fp)
        
        print(f"   Similarity: {verification['similarity']*100:.2f}%")
        print(f"   Frame diff: {verification['frame_diff']}")
        print(f"   Status: {'PASS ✅' if verification['passed'] else 'FAIL ❌'}")
        
        # Upload to MinIO
        print(f"\n📤 Uploading to storage...")
        _send_progress(video_id, {
            'type': 'upload',
            'quality': quality,
            'progress': 90,
            'status': 'Uploading to storage...'
        })
        
        object_name = f"transcoded/{video_id}/{quality}.mp4"
        
        minio_client.fput_object(
            bucket_name=os.getenv("MINIO_BUCKET"),
            object_name=object_name,
            file_path=str(output_path),
            content_type='video/mp4'
        )
        print(f"   ✅ Uploaded: {object_name}")
        
        # Save to database
        transcoded = TranscodedVideo(
            original_video_id=video_id,
            job_id=job.id,
            quality=quality,
            file_path=object_name,
            file_size=output_path.stat().st_size,
            duration=transcoded_fp['duration'],
            fingerprint_hash=transcoded_fp['signature_hash'],
            fingerprint_data=transcoded_fp,
            fingerprint_similarity=verification['similarity'] * 100,
            frame_count_matches=verification['frame_diff'] == 0
        )
        db.add(transcoded)
        
        # Update job
        job.status = 'verifying' if verification['passed'] else 'failed'
        job.verification_passed = verification['passed']
        job.verification_report = verification
        job.completed_at = datetime.now(timezone.utc)
        job.processing_time = (job.completed_at - job.started_at).total_seconds()
        
        if verification['passed']:
            job.status = 'completed'
        
        db.commit()
        
        # Send completion message
        _send_progress(video_id, {
            'type': 'completed',
            'quality': quality,
            'progress': 100,
            'status': f'{quality} completed ✅',
            'verification_passed': verification['passed']
        })
        
        # ═══════════════════════════════════════════════════════════
        # NEW: Record job completed in Prometheus
        # ═══════════════════════════════════════════════════════════
        duration = (datetime.now(timezone.utc) - started_time).total_seconds()
        record_job_complete(quality, duration)
        
        # Cleanup
        original_path.unlink()
        output_path.unlink()
        
        print(f"\n{'='*70}")
        print(f"✅ JOB COMPLETED")
        print(f"{'='*70}")
        print(f"   Processing time: {job.processing_time:.2f}s")
        print(f"   Verification: {'PASSED ✅' if verification['passed'] else 'FAILED ❌'}")
        
        return {
            'success': True,
            'job_id': job.id,
            'verification': verification
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # NEW: Record job failed in Prometheus
        # ═══════════════════════════════════════════════════════════
        record_job_failed(quality)
        
        _send_progress(video_id, {
            'type': 'error',
            'quality': quality,
            'status': f'Error: {str(e)}'
        })
        
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        
        raise
        
    finally:
        db.close()
        
        
def _run_ffmpeg_transcode(input_path: str, output_path: str, quality: str) -> bool:
    """
    Run FFmpeg transcoding
    
    Args:
        input_path: Input video path
        output_path: Output video path
        quality: Quality preset (360p, 480p, 720p, 1080p)
        
    Returns:
        True if successful
    """
    preset = QUALITY_PRESETS[quality]
    
    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f"scale={preset['resolution']}:force_original_aspect_ratio=decrease",
        '-c:v', 'libx264',
        '-b:v', preset['bitrate'],
        '-preset', 'medium',
        '-c:a', 'aac',
        '-b:a', preset['audio_bitrate'],
        '-movflags', '+faststart',  # Optimize for streaming
        '-y',
        output_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600 # 1 hour timeout
        )
        
        return result.returncode == 0
    
    except subprocess.TimeoutExpired:
        print("   ⏱️  Timeout!")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False