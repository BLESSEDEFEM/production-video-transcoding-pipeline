# Architecture: Distributed Video Transcoding Pipeline

This document explains the system design decisions, data flow, and trade-offs behind the video transcoding pipeline. It is written for engineers evaluating the project or onboarding to the codebase.

## System Overview

The pipeline follows a **producer-consumer architecture** with asynchronous job processing:

- **Producer**: The FastAPI backend receives video uploads, validates them, and enqueues transcoding jobs
- **Queue**: Redis (via RQ) holds pending jobs and distributes them to available workers
- **Consumers**: One or more RQ worker processes pick up jobs and execute the transcoding pipeline
- **Storage**: MinIO (S3-compatible) stores original and transcoded video files
- **Database**: PostgreSQL tracks all state (users, videos, jobs, quality metrics)
- **Real-time layer**: Redis pub/sub + WebSocket bridge delivers live progress to the browser

This separation means the API server never does CPU-heavy work. It stays responsive to user requests while workers handle the heavy FFmpeg processing in the background.

## Why This Architecture?

### Problem: Video Transcoding is CPU-Intensive and Slow

A 10-minute 1080p video can take 5-15 minutes to transcode to a single quality level. If the API server did this synchronously, it would block all other requests. Multiply by 3-4 quality levels per video, and a single upload could tie up the server for an hour.

### Solution: Async Job Queue with Horizontal Scaling

By pushing transcoding jobs to a Redis queue, we get three benefits:

1. **API stays fast** — upload returns immediately, transcoding happens in the background
2. **Horizontal scaling** — add more workers to process more jobs simultaneously (just change `replicas` in Kubernetes or `docker compose up --scale worker=4`)
3. **Fault tolerance** — if a worker crashes, the job stays in the queue and another worker picks it up

## Data Flow

### Upload → Transcode → Deliver
```
User uploads video
        │
        ▼
[FastAPI Backend]
        │
        ├── Save to MinIO (object storage)
        ├── Create Video record in PostgreSQL
        └── Run validation in background task
                │
                ├── Extract metadata (FFprobe)
                ├── Check codec, resolution, bitrate
                ├── Detect black/frozen frames
                ├── Generate perceptual fingerprint
                │
                ├── PASS → Enqueue jobs (one per quality)
                │           └── Redis Queue
                │                   │
                │           ┌───────┴───────┐
                │           │   RQ Worker   │
                │           │               │
                │           │ 1. Download from MinIO
                │           │ 2. Split into 4 chunks
                │           │ 3. Transcode chunks (parallel)
                │           │ 4. Verify each chunk
                │           │ 5. Assemble final video
                │           │ 6. Run quality metrics
                │           │ 7. Upload to MinIO
                │           │ 8. Update database
                │           │ 9. Send email notification
                │           └───────────────┘
                │
                └── FAIL → Reject video, notify user
```

### Real-Time Progress Flow
```
[RQ Worker] ──publish──▶ [Redis Pub/Sub] ──subscribe──▶ [FastAPI Listener] ──WebSocket──▶ [Browser]
     │                    channel: progress_{video_id}          │                              │
     │                                                          │                              │
     └── "Chunk 2/4 done"                                       └── ws_manager.send_progress() └── Live UI update
```

The worker publishes progress messages to a Redis channel. A background task in the FastAPI process subscribes to these channels and forwards messages through WebSocket connections to connected browsers. This decouples the worker (which runs in a separate process/container) from the WebSocket layer (which runs in the API server).

## Key Design Decisions

### 1. Chunked Parallel Processing

**Decision**: Split videos into N chunks and transcode them simultaneously.

**Why**: A 10-minute video transcoded sequentially takes ~10 minutes. Split into 4 chunks and transcoded in parallel, it takes ~3 minutes (not exactly 4x due to overhead from splitting, assembly, and thread management).

**Trade-off**: Chunked processing adds complexity — you need to handle chunk boundaries carefully to avoid visible glitches at join points. The assembly verification step exists specifically to catch these boundary issues.

**Implementation**: `video_splitter.py` uses FFmpeg's stream copy to split without re-encoding (fast). `parallel_processor.py` uses `ThreadPoolExecutor` to transcode chunks simultaneously. `chunk_assembler.py` uses FFmpeg's concat demuxer to join them.

### 2. Quality Verification at Multiple Levels

**Decision**: Verify quality at three stages — per-chunk, post-assembly, and post-transcode.

**Why**: Video corruption can happen at any stage. A chunk might have the wrong frame count (FFmpeg keyframe alignment). Assembly might introduce gaps or glitches at boundaries. The final video might have degraded quality beyond acceptable thresholds.

**Metrics used**:
- **PSNR** (Peak Signal-to-Noise Ratio): Measures pixel-level accuracy. Above 30dB is acceptable.
- **SSIM** (Structural Similarity Index): Measures perceptual similarity. Above 0.85 is acceptable.
- **VMAF** (Video Multi-method Assessment Fusion): Netflix's quality metric. Above 70 is acceptable.

**Trade-off**: Running quality metrics adds processing time (especially VMAF). But without verification, you might deliver corrupted videos to users — which is worse than a slightly longer pipeline.

### 3. Redis for Both Queue and Pub/Sub

**Decision**: Use Redis for job queuing (RQ) AND real-time progress (pub/sub).

**Why**: Redis is already required for the job queue, so using it for pub/sub avoids adding another service (like RabbitMQ or Kafka). Redis pub/sub is lightweight and perfect for ephemeral progress messages that don't need persistence.

**Trade-off**: If the API server restarts, it loses its pub/sub subscriptions momentarily. Progress messages during that window are lost. This is acceptable because progress is ephemeral — the user can refresh the page to reconnect.

### 4. MinIO Instead of Local Filesystem

**Decision**: Store all video files in MinIO (S3-compatible object storage) instead of the local filesystem.

**Why**: In a distributed system, workers might run on different machines. They all need access to the same video files. MinIO provides a shared storage layer accessible by any service via the S3 API. When you move to production, you can swap MinIO for AWS S3 with zero code changes — just change the endpoint URL.

**Trade-off**: Adds network overhead for upload/download. For a single-machine setup, local filesystem would be faster. But the S3-compatible API makes the architecture production-ready.

### 5. No Upscaling Policy

**Decision**: Never transcode to a quality higher than the original.

**Why**: Upscaling (e.g., 720p → 1080p) doesn't add real detail — it just makes the file bigger with interpolated pixels. The `get_appropriate_qualities()` function checks the original resolution and only queues jobs for equal or lower qualities. This saves processing time and storage.

### 6. Background Validation Instead of Synchronous

**Decision**: Video validation runs as a FastAPI `BackgroundTask`, not during the upload request.

**Why**: Validation involves FFprobe analysis, black frame detection, frozen frame detection, and fingerprint generation. This can take 5-30 seconds depending on video length. Making the user wait that long for their upload to complete would be poor UX. Instead, the upload returns immediately with status "uploaded", and validation runs in the background.

**Trade-off**: The user doesn't immediately know if their video is valid. They see "Validation in Progress" and get redirected to the progress page. The WebSocket connection delivers the result as soon as validation finishes.

## Database Schema

### Core Tables

- **users** — id, email, username, hashed_password
- **videos** — id, user_id, filename, status, resolution, codec, fingerprint_hash, inspection_report
- **transcoding_jobs** — id, video_id, quality, status, progress, verification_passed, processing_time
- **transcoded_videos** — id, original_video_id, job_id, quality, file_path, file_size, quality_score, fingerprint_similarity
- **video_chunks** — id, job_id, chunk_index, start_time, end_time, frames_match, verified

### Status Flow
```
Video:   uploaded → inspecting → approved → processing → completed
                               → rejected

Job:     pending → processing → verifying → completed
                              → failed
```

## Monitoring Strategy

### Prometheus Metrics

Metrics follow the RED method (Rate, Errors, Duration):

- **Rate**: `transcoding_jobs_total` — how many jobs per second
- **Errors**: `transcoding_jobs_total{status="failed"}` — failure rate
- **Duration**: `transcoding_job_duration_seconds` — how long jobs take

Plus operational metrics:
- `transcoding_queue_depth` — are jobs piling up?
- `active_workers` — do we have enough workers?
- `process_resident_memory_bytes` — is the API leaking memory?

### Grafana Dashboard

10 panels organized in 3 rows:
1. **Counters row**: uploads, completed jobs, failed jobs, emails sent
2. **Gauges row**: queue depth, active workers, jobs in progress, memory
3. **Time series row**: jobs per minute rate, p95 job duration

## Scaling Considerations

### Current Limitations (Single Machine)

- Workers share CPU with the API server and database
- MinIO storage is limited to local disk
- No load balancing for the API

### Production Scaling Path

1. **More workers**: `kubectl scale deployment transcoding-worker --replicas=8`
2. **Separate databases**: Move PostgreSQL and Redis to managed services (RDS, ElastiCache)
3. **S3 storage**: Replace MinIO with AWS S3 (just change `MINIO_ENDPOINT`)
4. **API load balancing**: Kubernetes Service with multiple backend replicas
5. **CDN delivery**: Serve transcoded videos through CloudFront or similar
6. **GPU transcoding**: Use NVIDIA NVENC for 10-20x faster encoding

## Security Notes

- JWT authentication on all API endpoints
- Password hashing with bcrypt
- MinIO credentials stored in environment variables (not in code)
- Kubernetes secrets for production credential management
- File type validation before processing (rejects non-video files)
- File size limits (2GB max upload)