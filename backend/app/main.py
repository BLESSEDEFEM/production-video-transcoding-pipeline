from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from app.websocket_manager import ws_manager
from app.api.auth import router as auth_router
from app.api import videos
from pathlib import Path
from contextlib import asynccontextmanager
import shutil
import asyncio
import redis.asyncio as redis
# The Synchronous library (for core types or legacy logic)
import redis as redis_lib
import json
import os

# Strong reference set to prevent garbage collection
background_tasks = set()


async def redis_listener():
    """
    SOLUTION 1: Use get_message() instead of async for loop
    SOLUTION 2: Properly handle cleanup
    """
    redis_url = os.getenv("REDIS_URL")
    redis_client = await redis.from_url(redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    
    await pubsub.psubscribe('progress_*')
    print("🎧 Redis listener started - monitoring progress_*")
    
    try:
        while True:
            # CRITICAL: Use get_message() NOT async for loop
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message and message['type'] == 'pmessage':
                try:
                    channel = message['channel']
                    video_id = int(channel.split('_')[1])
                    data = json.loads(message['data'])
                    
                    await ws_manager.send_progress(video_id, data)
                    print(f"📤 Forwarded to video {video_id}: {data.get('status', 'N/A')}")
                except Exception as e:
                    print(f"⚠️  Message processing error: {e}")
            
            # Yield control to event loop
            await asyncio.sleep(0.01)
            
    except asyncio.CancelledError:
        print("🛑 Redis listener cancelled")
    except Exception as e:
        print(f"❌ Redis listener error: {e}")
    finally:
        await pubsub.punsubscribe('progress_*')
        await pubsub.close()
        await redis_client.aclose()
        print("✅ Redis listener cleanup complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    SOLUTION 3: Use lifespan context manager
    SOLUTION 4: Store strong reference
    """
    # Start Redis listener with strong reference
    task = asyncio.create_task(redis_listener())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    
    # Start metrics updater
    metrics_task = asyncio.create_task(update_queue_metrics())
    background_tasks.add(metrics_task)
    metrics_task.add_done_callback(background_tasks.discard)
    
    print("✅ Background tasks started")
    
    yield  # App runs here
    
    # Graceful shutdown
    print("🛑 Shutting down background tasks...")
    for t in background_tasks:
        t.cancel()
    
    # Wait for cancellation
    await asyncio.gather(*background_tasks, return_exceptions=True)
    print("✅ Background tasks stopped")


app = FastAPI(
    title="Video Transcoding API",
    lifespan=lifespan  # CRITICAL: Use lifespan parameter
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(videos.router)

# Directories
UPLOAD_DIR = Path("storage/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def read_root():
    return {
        "message": "Video Transcoding API",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Unified health check endpoint for Kubernetes (Liveness/Readiness probes)
    and external monitoring.
    
    Kubernetes calls this every 10 seconds.
    If it gets 3 failures in a row, it restarts the pod.
    Returns 200 OK with service metadata to confirm the container is responsive.
    """
    return {
        "status": "healthy",
        "service": "video-transcoding-backend",
        "version": "1.0.0"  # Helpful for verifying which image version is live
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus scrapes this endpoint every 15 seconds.

    Returns metrics in Prometheus text format:
    # HELP jobs_total Total transcoding jobs
    # TYPE jobs_total counter
    transcoding_jobs_total{quality="720p",status="completed"} 15.0
    ...
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
    

@app.websocket("/ws/progress/{video_id}")
async def websocket_progress(websocket: WebSocket, video_id: int):
    """WebSocket endpoint for progress updates"""
    await ws_manager.connect(websocket, video_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, video_id)


@app.post("/api/validate")
async def validate_video(video: UploadFile = File(...)):
    """Validate uploaded video"""
    temp_path = None
    
    try:
        temp_dir = Path("storage/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / video.filename
        
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        from app.services.video_validator import VideoValidator
        validator = VideoValidator()
        is_valid, checks = validator.validate(str(temp_path))
        
        checks_json = [
            {
                "name": check.name,
                "passed": check.passed,
                "level": check.level.value,
                "message": check.message
            }
            for check in checks
        ]
        
        if is_valid:
            final_path = UPLOAD_DIR / video.filename
            shutil.move(str(temp_path), str(final_path))
            
            return {
                "is_valid": True,
                "filename": video.filename,
                "size": final_path.stat().st_size,
                "checks": checks_json
            }
        else:
            temp_path.unlink()
            
            return {
                "is_valid": False,
                "filename": video.filename,
                "checks": checks_json
            }
        
    except Exception as e:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        
        return {
            "is_valid": False,
            "error": str(e)
        }
        
        
async def update_queue_metrics():
    """
    Background task: every 30 seconds, check Redis queue depth
    and update the Prometheus gauge.

    Why a loop? Because we want the gauge to ALWAYS reflect the
    current real depth, not just when a job starts/ends.
    """
    from app.metrics import queue_depth, active_workers

    r = redis_lib.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )

    while True:
        try:
            # RQ stores queued jobs in "rq:queue:transcoding"
            depth = r.llen("rq:queue:transcoding")
            queue_depth.set(depth)

            # Count active workers using RQ worker list
            worker_count = len(r.smembers("rq:workers"))
            active_workers.set(worker_count)

        except Exception:
            pass  # Don't crash if Redis is temporarily unavailable

        await asyncio.sleep(30)   # Wait 30 seconds, then repeat