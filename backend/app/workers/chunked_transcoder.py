"""
Chunked Transcoder - the full Download to Upload pipeline:
1. Download video from MinIO
2. Split into chunks
3. Transcode chunks in parallel (with WebSocket updates)
4. Assemble chunks
5. Run quality check (send results via WebSocket)
6. Upload final video to MinIO
7. Update database
"""
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.video import Video, VideoStatus
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.models.user import User
from app.services.video_splitter import split_video
from app.workers.parallel_processor import process_chunks_in_parallel
from app.services.chunk_assembler import assemble_chunks
from app.services.quality_metrics import QualityMetrics
from app.services.assembly_verifier import verify_assembly
import os
import redis
import json
from app.metrics import (
    record_job_started,
    record_job_complete,
    record_job_failed,
    jobs_in_progress,
    queue_depth
)


QUALITY_PRESETS = ['360p', '480p', '720p', '1080p']


async def transcode_video_chunked(video_id: int, quality: str, num_chunks: int = 4):
    """
    Full chunked transcoding pipeline for ONE quality level.
    Sends WebSocket updates at every stage.
    """
    db = SessionLocal()
    temp_dir = Path(f"temp_transcoding/video_{video_id}_{quality}")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    video = None
    job = None
    
    async def update(message: dict):
        """Send progress via Redis pub/sub so the FastAPI listener can forward to WebSocket."""
        try:
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
            r.publish(f'progress_{video_id}', json.dumps(message))
        except Exception as e:
            print(f"⚠️  Progress update failed: {e}")
        
    try:
        print(f"\n{'='*60}")
        print(f"🎬 CHUNKED TRANSCODE: video={video_id}, quality={quality}")
        print(f"{'='*60}")
        
        # ── STEP 1: GET VIDEO FROM DATABASE ──
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found in database")
        
        # Create job record
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
        # PROMETHEUS METRICS: Record job started
        # ═══════════════════════════════════════════════════════════
        record_job_started(quality)
        started_time = datetime.now(timezone.utc)
        
        # ── STEP 2: DOWNLOAD ORIGINAL FROM MINIO ──
        await update({
            "type": "downloading",
            "status": f"📥 Downloading original video..."
        })
        
        from app.storage import minio_client
        bucket = os.getenv("MINIO_BUCKET", "videos")
        original_path = temp_dir / "original.mp4"
        
        minio_client.fget_object(
            bucket_name=bucket,
            object_name=video.original_path,
            file_path=str(original_path)
        )
        print(f"✅ Downloaded: {original_path}")
        
        # ── STEP 3: SPLIT INTO CHUNKS ──
        await update({
            "type": "splitting",
            "status": f"✂️  Splitting into {num_chunks} chunks..."
        })
        
        chunks = split_video(
            video_path=str(original_path),
            num_chunks=num_chunks,
            output_dir=str(temp_dir / "original_chunks")
        )
        
        await update({
            "type": "split_done",
            "total_chunks": len(chunks),
            "status": f"✅ Split into {len(chunks)} chunks"
        })
        
        # ── STEP 4: TRANSCODE CHUNKS IN PARALLEL ──
        parallel_result = await process_chunks_in_parallel(
            chunks=chunks,
            quality=quality,
            output_dir=str(temp_dir / "transcoded_chunks"),
            video_id=video_id  # <- pass video_id for WebSocket updates
        )
        
        if not parallel_result['all_passed']:
            raise Exception(f"Only {parallel_result['success_count']}/{len(chunks)} chunks succeeded")
        
        # ── STEP 5: ASSEMBLY VERIFICATION ──
        await update({
            "type": "assembling",
            "status": "🔧 Verifying boundaries and assembling..."
        })

        final_path = str(temp_dir / f"final_{quality}.mp4")
        assembled = assemble_chunks(parallel_result['results'], final_path)

        if not assembled:
            raise Exception("Assembly failed")

        # ── VERIFY THE ASSEMBLED VIDEO ──
        print("\n🔍 Verifying assembled video...")
        assembly_report = verify_assembly(
            original_path=str(original_path),
            assembled_path=final_path
        )

        # Send assembly verification result to frontend
        await update({
            "type": "assembly_verified",
            "passed": assembly_report["passed"],
            "duration_ok": assembly_report["duration_ok"],
            "frames_ok": assembly_report["frames_ok"],
            "decode_ok": assembly_report["decode_ok"],
            "original_duration": assembly_report.get("original_duration"),
            "assembled_duration": assembly_report.get("assembled_duration"),
            "details": assembly_report["details"],
            "status": f"{'✅' if assembly_report['passed'] else '⚠️'} Assembly: {assembly_report['details']}"
        })

        if not assembly_report["passed"]:
            raise Exception(f"Assembly verification failed: {assembly_report['details']}")
        
        # ── STEP 6: QUALITY METRICS ──
        qm = QualityMetrics()
        quality_result = qm.run_quality_check(str(original_path), final_path, include_vmaf=True)
        
        # Send quality metrics to frontend dashboard
        vmaf_score = quality_result.get('vmaf')
        await update({
            "type": "quality_result",
            "psnr": quality_result['psnr'],
            "ssim": quality_result['ssim'],
            "vmaf": vmaf_score,
            "psnr_ok": quality_result['psnr_ok'],
            "ssim_ok": quality_result['ssim_ok'],
            "vmaf_ok": (vmaf_score or 0) >= 70,
            "overall_pass": quality_result['overall_pass'],
            "status": (
                f"📊 Quality — PSNR: {quality_result['psnr']:.1f}dB, "
                f"SSIM: {quality_result['ssim']:.4f}"
                + (f", VMAF: {quality_result.get('vmaf', 0):.1f}" if quality_result.get('vmaf') else "")
                + f" ({'✅ PASS' if quality_result['overall_pass'] else '⚠️ CHECK'})"
            )
        })
        
        # ── STEP 7: UPLOAD FINAL VIDEO TO MINIO ──
        await update({
            "type": "uploading",
            "status": f"📤 Uploading {quality} to storage..."
        })
        
        object_name = f"transcoded/{video_id}/{quality}.mp4"
        minio_client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=final_path,
            content_type='video/mp4'
        )
        
        # ── STEP 8: SAVE TO DATABASE ──
        transcoded = TranscodedVideo(
            original_video_id=video_id,
            job_id=job.id,
            quality=quality,
            file_path=object_name,
            file_size=Path(final_path).stat().st_size,
            quality_score=quality_result['ssim'],
            fingerprint_similarity=quality_result['ssim'] * 100 if quality_result['ssim'] else None
        )
        db.add(transcoded)
        
        job.status = 'completed'
        job.verification_passed = quality_result['overall_pass']
        job.completed_at = datetime.now(timezone.utc)
        job.processing_time = (job.completed_at - job.started_at).total_seconds()
        db.commit()
        
        # ═══════════════════════════════════════════════════════════
        # PROMETHEUS METRICS: Record job completed successfully
        # ═══════════════════════════════════════════════════════════
        duration = (datetime.now(timezone.utc) - started_time).total_seconds()
        record_job_complete(quality, duration)
        
        # ── DONE ──
        await update({
            "type": "job_complete",
            "quality": quality,
            "status": f"🎉 {quality} complete! ({job.processing_time:.1f}s total)"
        })
        
        # Check if ALL qualities for this video are now complete
        try:
            all_jobs = db.query(TranscodingJob).filter(
                TranscodingJob.video_id == video_id
            ).all()
            
            completed_count = sum(1 for j in all_jobs if j.status == 'completed')
            total_count = len(all_jobs)
            
            if completed_count == total_count and total_count > 0:
                # All qualities done — send completion email
                user = db.query(User).filter(User.id == video.user_id).first()
                if user:
                    transcoded = db.query(TranscodedVideo).filter(
                        TranscodedVideo.original_video_id == video_id
                    ).all()
                    
                    versions = [
                        {
                            "quality": t.quality,
                            "file_size_mb": round((t.file_size or 0) / 1024 / 1024, 2),
                            "similarity_score": round(t.fingerprint_similarity or 0, 1),
                            "verification_passed": any(
                                j.verification_passed for j in all_jobs if j.quality == t.quality
                            )
                        }
                        for t in transcoded
                    ]
                    
                    total_time = sum(j.processing_time or 0 for j in all_jobs)
                    
                    from app.services.email_service import notify_transcoding_complete
                    notify_transcoding_complete(
                        to_email=user.email,
                        filename=video.filename,
                        video_id=video_id,
                        transcoded_versions=versions,
                        total_time=total_time
                    )
                    
                    # Update video status to completed
                    video.status = VideoStatus.COMPLETED
                    db.commit()
        except Exception as e:
            print(f"⚠️  Completion email failed (non-fatal): {e}")
        
        return {"success": True, "job_id": job.id, "quality": quality}
    
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # PROMETHEUS METRICS: Record job failed
        # ═══════════════════════════════════════════════════════════
        record_job_failed(quality)
        
        await update({
            "type": "job_failed",
            "error": str(e),
            "status": f"❌ Failed: {e}"
        })
        
        if job is not None:
            job.status = 'failed'
            job.error_message = str(e)
            db.commit()
        
        # Send failure email notification
        try:
            if video is not None:
                user = db.query(User).filter(User.id == video.user_id).first()
                if user:
                    from app.services.email_service import notify_transcoding_failed
                    notify_transcoding_failed(
                        to_email=user.email,
                        filename=video.filename,
                        video_id=video_id,
                        quality=quality,
                        error=str(e)
                    )
        except Exception as email_err:
            print(f"⚠️  Failure email failed (non-fatal): {email_err}")
            
        return {"success": False, "error": str(e)}
    
    finally:
        db.close()
        
def transcode_video_chunked_sync(video_id: int, quality: str, num_chunks: int = 4):
    """
    Synchronous wrapper for RQ workers.
    
    RQ can't run async functions directly, so this wrapper
    creates an event loop and runs the async function inside it.
    This is the function that gets called from the Redis queue.
    """
    import asyncio
    
    # Create a new event loop for this worker thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            transcode_video_chunked(video_id, quality, num_chunks)
        )
        return result
    finally:
        loop.close()