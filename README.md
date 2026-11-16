Distributed Video Transcoding Pipeline

A distributed video transcoding system that splits videos into chunks, transcodes them in parallel across multiple workers, verifies output quality using industry-standard metrics (PSNR, SSIM, VMAF), and reassembles the final output — with real-time progress tracking via WebSocket.

Built with FastAPI, Next.js, FFmpeg, Redis (RQ), PostgreSQL, MinIO, and Docker. Includes Prometheus + Grafana monitoring and Kubernetes deployment manifests.


How It Works

Upload → Validate → Fingerprint → Split → Transcode (parallel) → Verify → Assemble → Notify


Upload — User uploads a video via the React frontend
Validation — Backend inspects the file: codec, resolution, bitrate, black frame detection, frozen frame detection
Fingerprinting — Perceptual hash generated for duplicate detection and integrity verification
Approval/Rejection — Video passes validation (queued) or is rejected with specific reasons
Queue — Approved videos enter the Redis queue with one job per target quality (360p, 480p, 720p, 1080p)
Chunked Split — Worker downloads the original from MinIO, splits it into N equal-duration segments via FFmpeg
Parallel Transcode — All chunks are transcoded simultaneously using a thread pool
Per-Chunk Verification — Each chunk is verified for frame count accuracy and duration correctness
Assembly — Transcoded chunks are concatenated into the final video
Quality Metrics — PSNR, SSIM, and VMAF scores are calculated against the original to verify output fidelity
Notification — User receives a styled HTML email when all quality variants are complete



Architecture
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI    │────▶│ PostgreSQL  │
│  Frontend   │◀────│   Backend    │     │  Database   │
│  (port 3000)│ WS  │  (port 8000) │     │ (port 5432) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │              │
              ┌─────▼─────┐ ┌─────▼─────┐
              │   Redis   │ │   MinIO   │
              │   Queue   │ │  Storage  │
              │(port 6379)│ │(port 9000)│
              └─────┬─────┘ └───────────┘
                    │
            ┌───────┴────────┐
            │   RQ Workers   │
            │   (1-N pods)   │
            │                │
            │ Split → Transcode → Verify → Assemble
            └────────────────┘

    ┌──────────────┐     ┌─────────────┐
    │  Prometheus  │────▶│   Grafana   │
    │  (port 9090) │     │ (port 3001) │
    └──────────────┘     └─────────────┘
```

Tech Stack

LayerTechnologyWhyAPIFastAPIAsync Python, WebSocket support, auto-generated API docsFrontendNext.js 16 + TypeScript + TailwindApp Router, server components, type safetyDatabasePostgreSQL + SQLAlchemy + AlembicRelational model for users, videos, jobs; migration supportQueueRedis + RQ (Redis Queue)Simple job queue with pub/sub for real-time progress updatesStorageMinIOS3-compatible object storage — same API as AWS S3, runs locallyTranscodingFFmpegIndustry standard for video processing, splitting, assembly, quality analysisMonitoringPrometheus + GrafanaCustom metrics: queue depth, worker count, job duration, memory usageInfrastructureDocker Compose (8 services) + Kubernetes manifestsSingle-command local setup; production-ready K8s configs with scaling


Key Technical Decisions

Why chunked parallel processing instead of single-file transcoding?
A 10-minute video transcoded sequentially takes N minutes. Split into 10 chunks across 10 workers, it takes roughly N/10 minutes. The tradeoff is coordination complexity — chunk boundaries must align on keyframes, and assembly requires precise concatenation to avoid audio/video sync drift. I use FFmpeg's segment muxer with keyframe-aligned splitting to handle this.

Why three quality metrics (PSNR, SSIM, VMAF)?
PSNR measures raw signal fidelity but doesn't correlate well with human perception. SSIM accounts for structural similarity. VMAF (Netflix's metric) is the most perceptually accurate but computationally expensive. Using all three provides a complete quality picture — if VMAF is high but PSNR is low, the transcode is perceptually good despite mathematical differences.

Why MinIO instead of direct filesystem storage?
MinIO speaks the S3 API, so the code is directly portable to AWS S3 without changing a single line. It also handles concurrent reads/writes from multiple workers cleanly, which filesystem storage doesn't guarantee without locking.

Why Redis for both queue and real-time updates?
RQ (Redis Queue) handles job distribution to workers. Redis pub/sub pushes progress updates to the FastAPI WebSocket handler, which streams them to the browser. Using one system for both avoids adding a separate message broker (like RabbitMQ) and keeps the infrastructure simpler.

Why perceptual fingerprinting on upload?
Perceptual hashing generates a content-based fingerprint that survives re-encoding. This enables duplicate detection (don't re-transcode the same video) and integrity verification (confirm the assembled output matches the original input).


Monitoring

Grafana dashboard (http://localhost:3001, login: admin / admin123) with 10 panels:


Videos uploaded, jobs completed, jobs failed, emails sent
Queue depth gauge, active workers, jobs in progress
Backend memory usage
Jobs per minute rate
Job duration (p95) histogram


Custom Prometheus metrics:


videos_uploaded_total — upload counter by status
transcoding_jobs_total — job counter by quality and status
transcoding_queue_depth — current queue size
active_workers — number of RQ workers
transcoding_job_duration_seconds — job duration histogram
emails_sent_total — email counter by success/failure



API Reference

Authentication

MethodEndpointDescriptionPOST/api/auth/registerCreate new userPOST/api/auth/loginLogin, returns JWTGET/api/auth/meGet current user

Videos

MethodEndpointDescriptionPOST/api/uploadUpload video fileGET/api/videos/listList user's videosGET/api/videos/{id}/inspectionValidation reportGET/api/videos/{id}/summaryTranscoding summaryGET/api/videos/{id}/download/{quality}Download transcoded videoPOST/api/videos/{id}/cancelCancel transcodingDELETE/api/videos/{id}Delete video and all versions

Admin

MethodEndpointDescriptionGET/api/admin/statsSystem statisticsGET/api/admin/videosAll videos (filterable)GET/api/admin/jobsAll jobs (filterable)GET/api/admin/healthService health check

System

MethodEndpointDescriptionGET/healthKubernetes health probeGET/metricsPrometheus metricsWS/ws/progress/{video_id}Real-time progress


Getting Started

Prerequisites


Docker & Docker Compose
(Optional for local dev) Python 3.11+, Node.js 18+, FFmpeg


Run with Docker Compose

bashgit clone https://github.com/BLESSEDEFEM/video-transcoding-pipeline.git
cd video-transcoding-pipeline
docker compose up -d

This starts all 8 services:

ServiceURLPurposeFrontendhttp://localhost:3000React UIBackendhttp://localhost:8000FastAPI APIGrafanahttp://localhost:3001MonitoringPrometheushttp://localhost:9090MetricsMinIOhttp://localhost:9001Storage consolePostgreSQLlocalhost:5432DatabaseRedislocalhost:6379Queue & pub/sub

Run Locally (Development)

bash# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
cd backend
python start_worker.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

Kubernetes Deployment

bashkubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml

# Scale workers based on load
kubectl scale deployment transcoding-worker -n video-app --replicas=8


Tests

bashcd backend
pip install pytest httpx
python -m pytest tests/test_api.py -v

24 tests covering: health endpoints, user auth, video upload/inspection/summary/cancellation, admin dashboard with filtering, and monitoring endpoints.


Project Structure
```
video-transcoding-pipeline/
├── backend/
│   ├── app/
│   │   ├── api/            # API endpoints (auth, videos, admin)
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── services/       # Quality metrics, email, business logic
│   │   ├── workers/        # Transcoding workers (chunked, parallel)
│   │   ├── inspection/     # Video validation and fingerprinting
│   │   ├── queue/          # Redis queue configuration
│   │   ├── main.py         # FastAPI entry point
│   │   └── metrics.py      # Prometheus metric definitions
│   ├── tests/              # 24 automated tests
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js pages (login, upload, progress, admin)
│   ├── components/         # Shared React components
│   ├── Dockerfile
│   └── package.json
├── k8s/                    # Kubernetes deployment manifests
├── monitoring/
│   ├── prometheus.yml      # Scrape config
│   └── grafana/            # Dashboard provisioning
└── docker-compose.yml      # 8-service orchestration
```

License

MIT
