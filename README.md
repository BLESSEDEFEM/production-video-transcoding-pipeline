# Distributed Video Transcoding Pipeline

A production-grade distributed video transcoding system built with FastAPI, React, FFmpeg, Redis, PostgreSQL, and Docker. Supports chunked parallel processing, real-time WebSocket progress tracking, quality verification, and comprehensive monitoring.

## What It Does

Upload a video → automatic validation & fingerprinting → split into chunks → transcode each chunk in parallel across multiple workers → verify quality (PSNR, SSIM, VMAF) → assemble final output → notify user via email.

This is the kind of system that powers video processing at companies like YouTube, Netflix, and Vimeo — scaled down to a single-machine deployment for demonstration purposes.

## Key Features

- **Chunked Parallel Transcoding**: Videos are split into chunks and transcoded simultaneously across multiple workers, dramatically reducing processing time
- **Quality Verification**: Every transcoded video is verified using industry-standard metrics (PSNR, SSIM, VMAF) to ensure output quality
- **Video Fingerprinting**: Perceptual hashing generates unique fingerprints for each video, enabling duplicate detection and integrity verification
- **Real-Time Progress**: WebSocket connections push live updates to the browser — see each chunk complete in real time
- **Smart Quality Selection**: Automatically determines appropriate output qualities based on source resolution (never upscales)
- **Email Notifications**: Sends styled HTML emails on upload approval, rejection, transcoding completion, and failures
- **Admin Dashboard**: System-wide monitoring with stats, video/job tables, filtering, and service health checks
- **Prometheus + Grafana Monitoring**: Custom metrics for uploads, jobs, queue depth, worker count, processing times, and memory usage
- **Docker + Kubernetes Ready**: Full Docker Compose setup with 8 services, plus Kubernetes manifests for cloud deployment

## Tech Stack

### Backend
- **FastAPI** — async Python API framework
- **PostgreSQL** — relational database for users, videos, jobs
- **Redis** — job queue (RQ) and pub/sub for real-time updates
- **MinIO** — S3-compatible object storage for video files
- **FFmpeg** — video transcoding, splitting, assembly, and quality analysis
- **SQLAlchemy** — ORM with Alembic migrations
- **Prometheus** — metrics collection
- **Grafana** — metrics visualization dashboards

### Frontend
- **Next.js 16** — React framework with App Router
- **TypeScript** — type-safe frontend code
- **Tailwind CSS** — utility-first styling
- **Axios** — HTTP client
- **Lucide React** — icon library

### Infrastructure
- **Docker Compose** — 8-service orchestration
- **Kubernetes** — deployment manifests with scaling configs
- **SendGrid / SMTP** — email delivery (with console fallback)

## Architecture
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
            │  RQ Workers    │
            │  (1-N pods)    │
            │                │
            │ Split → Transcode → Verify → Assemble
            └────────────────┘

    ┌──────────────┐     ┌─────────────┐
    │  Prometheus  │────▶│   Grafana   │
    │  (port 9090) │     │ (port 3001) │
    └──────────────┘     └─────────────┘
```

## Video Processing Pipeline

1. **Upload** — User uploads video via the React frontend
2. **Validation** — Backend inspects the video: codec check, resolution check, bitrate check, black frame detection, frozen frame detection
3. **Fingerprinting** — Perceptual hash generated for duplicate detection and later verification
4. **Approval/Rejection** — Video either passes validation (queued for transcoding) or is rejected with reasons
5. **Queue** — Approved videos are added to the Redis queue with one job per target quality (360p, 480p, 720p, 1080p)
6. **Chunked Split** — Worker downloads the original from MinIO and splits it into N equal chunks using FFmpeg
7. **Parallel Transcode** — All chunks are transcoded simultaneously using a thread pool
8. **Per-Chunk Verification** — Each chunk is verified for frame count accuracy and duration correctness
9. **Assembly** — Transcoded chunks are concatenated into the final video
10. **Assembly Verification** — Final video is checked for duration accuracy, frame count, and decode errors
11. **Quality Metrics** — PSNR, SSIM, and VMAF scores are calculated against the original
12. **Storage** — Final transcoded video is uploaded to MinIO
13. **Notification** — User receives an email when all qualities are complete

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- FFmpeg (installed automatically in Docker)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/video-transcoding-pipeline.git
cd video-transcoding-pipeline
```

### 2. Environment Variables

Create `backend/.env.example`:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/video_transcoding
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=videos
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Run with Docker Compose (Recommended)
```bash
docker compose up -d
```

This starts all 8 services:

| Service    | URL                    | Purpose                    |
|------------|------------------------|----------------------------|
| Frontend   | http://localhost:3000   | React UI                   |
| Backend    | http://localhost:8000   | FastAPI API                |
| Grafana    | http://localhost:3001   | Monitoring dashboards      |
| Prometheus | http://localhost:9090   | Metrics collection         |
| MinIO      | http://localhost:9001   | Storage console            |
| PostgreSQL | localhost:5432         | Database                   |
| Redis      | localhost:6379         | Queue & pub/sub            |

### 4. Run Locally (Development)
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker (separate terminal)
cd backend
python start_worker.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Running Tests
```bash
cd backend
pip install pytest httpx
python -m pytest tests/test_api.py -v
```

24 automated tests covering:
- Health and metrics endpoints
- User registration and authentication
- Video listing, inspection, summary, and cancellation
- Admin dashboard stats, videos, and jobs with filtering

## Monitoring

### Grafana Dashboard (http://localhost:3001)

Login: `admin` / `admin123`

10-panel dashboard with:
- Videos uploaded, jobs completed, jobs failed, emails sent
- Queue depth gauge, active workers, jobs in progress
- Backend memory usage
- Jobs per minute rate graph
- Job duration (p95) histogram

### Prometheus (http://localhost:9090)

Custom metrics:
- `videos_uploaded_total` — upload counter by status
- `transcoding_jobs_total` — job counter by quality and status
- `transcoding_queue_depth` — current queue size
- `active_workers` — number of RQ workers
- `jobs_in_progress` — currently processing jobs
- `transcoding_job_duration_seconds` — job duration histogram
- `emails_sent_total` — email counter by success/failure

## API Endpoints

### Authentication
- `POST /api/auth/register` — Create new user
- `POST /api/auth/login` — Login, returns JWT token
- `GET /api/auth/me` — Get current user

### Videos
- `POST /api/upload` — Upload video file
- `GET /api/videos/list` — List user's videos
- `GET /api/videos/{id}/inspection` — Get validation report
- `GET /api/videos/{id}/summary` — Get transcoding summary
- `GET /api/videos/{id}/download/{quality}` — Download transcoded video
- `POST /api/videos/{id}/cancel` — Cancel transcoding jobs
- `DELETE /api/videos/{id}` — Delete video and all versions

### Admin
- `GET /api/admin/stats` — System statistics
- `GET /api/admin/videos` — All videos (with filtering)
- `GET /api/admin/jobs` — All jobs (with filtering)
- `GET /api/admin/health` — Service health check

### System
- `GET /health` — Kubernetes health probe
- `GET /metrics` — Prometheus metrics
- `WS /ws/progress/{video_id}` — WebSocket progress updates

## Kubernetes Deployment
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml
```

Scale workers based on load:
```bash
kubectl scale deployment transcoding-worker -n video-app --replicas=8
```

## Project Structure
```
video-transcoding-pipeline/
├── backend/
│   ├── app/
│   │   ├── api/            # API endpoints (auth, videos, admin)
│   │   ├── models/         # SQLAlchemy database models
│   │   ├── services/       # Business logic (quality metrics, email, etc.)
│   │   ├── workers/        # Transcoding workers (chunked, parallel)
│   │   ├── inspection/     # Video validation and fingerprinting
│   │   ├── queue/          # Redis queue configuration
│   │   ├── utils/          # Auth helpers, dependencies
│   │   ├── main.py         # FastAPI app entry point
│   │   └── metrics.py      # Prometheus metric definitions
│   ├── tests/              # Automated pytest test suite
│   ├── Dockerfile          # Backend container
│   ├── Dockerfile.worker   # Worker container
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── app/                # Next.js pages (login, upload, progress, admin)
│   ├── components/         # Shared React components (Navbar)
│   ├── Dockerfile          # Frontend container
│   └── package.json        # Node dependencies
├── k8s/                    # Kubernetes deployment manifests
├── monitoring/
│   ├── prometheus.yml      # Prometheus scrape config
│   └── grafana/            # Grafana provisioning (datasource + dashboard)
└── docker-compose.yml      # Full stack orchestration (8 services)
```

## License

MIT