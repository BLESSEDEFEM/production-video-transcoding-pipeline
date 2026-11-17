# Video Transcoding Pipeline

A queue-based video transcoding system that splits videos into chunks, transcodes them with FFmpeg in background workers, scores output quality with PSNR and SSIM, and reassembles the final output — with real-time progress tracking via WebSocket.

Built with FastAPI, Next.js, FFmpeg, Redis (RQ), PostgreSQL, MinIO, and Docker. Includes Prometheus + Grafana monitoring. Kubernetes manifests are included but experimental (not run in production).

## How It Works

```
Upload → Validate → Fingerprint → Split → Transcode (parallel) → Verify → Assemble → Notify
```

1. **Upload** — User uploads a video via the Next.js frontend
2. **Validation** — Backend inspects the file: codec, resolution, bitrate, black frame detection, frozen frame detection
3. **Fingerprinting** — Perceptual hash generated for duplicate detection and integrity verification
4. **Approval/Rejection** — Video passes validation (queued) or is rejected with specific reasons
5. **Queue** — Approved videos enter the Redis queue with one job per target quality (360p, 480p, 720p, 1080p)
6. **Chunked Split** — Worker downloads the original from MinIO and splits it into N equal-duration segments via FFmpeg
7. **Parallel Transcode** — Chunks are transcoded concurrently using a thread pool
8. **Per-Chunk Verification** — Each chunk is checked for frame count and duration
9. **Assembly** — Transcoded chunks are concatenated into the final video
10. **Quality Metrics** — PSNR and SSIM scores are calculated against the original to verify output fidelity
11. **Notification** — User receives an HTML email when all quality variants are complete

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
            │   RQ Workers   │
            │   (1–N)        │
            │                │
            │ Split → Transcode → Verify → Assemble
            └────────────────┘

    ┌──────────────┐     ┌─────────────┐
    │  Prometheus  │────▶│   Grafana   │
    │  (port 9090) │     │ (port 3001) │
    └──────────────┘     └─────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI | Async Python, WebSocket support, auto-generated API docs |
| Frontend | Next.js 16 + TypeScript + Tailwind | App Router, server components, type safety |
| Database | PostgreSQL + SQLAlchemy + Alembic | Relational model for users, videos, jobs; migration support |
| Queue | Redis + RQ (Redis Queue) | Simple job queue with pub/sub for real-time progress updates |
| Storage | MinIO | S3-compatible object storage — same API as AWS S3, runs locally |
| Transcoding | FFmpeg | Industry standard for video processing, splitting, assembly, quality analysis |
| Monitoring | Prometheus + Grafana | Custom metrics: queue depth, worker count, job duration, memory usage |
| Infrastructure | Docker Compose (8 services) + experimental Kubernetes manifests | Single-command local setup |

## Key Technical Decisions

### Why chunked parallel processing instead of single-file transcoding?

A 10-minute video transcoded sequentially takes N minutes. Split into 10 chunks across 10 workers, it should take roughly N/10 minutes (expected speed-up; not benchmarked yet). The trade-off is coordination complexity: chunk boundaries must align on keyframes, and assembly needs precise concatenation to avoid audio/video sync drift. FFmpeg's segment muxer with keyframe-aligned splitting handles this. Known issue: assembly currently adds a few frames at chunk boundaries (see [Known Issues](#known-issues)).

### Why two quality metrics (PSNR, SSIM)?

PSNR measures raw signal fidelity but doesn't match human perception well. SSIM accounts for structural similarity. VMAF (Netflix's perceptual metric) was planned, but the FFmpeg build used here doesn't include libvmaf, so it is not active.

### Why MinIO instead of direct filesystem storage?

MinIO speaks the S3 API, so moving to AWS S3 is a configuration change rather than a code change. It also handles concurrent reads/writes from multiple workers cleanly, which filesystem storage doesn't guarantee without locking.

### Why Redis for both queue and real-time updates?

RQ (Redis Queue) hands jobs to workers. Redis pub/sub pushes progress updates to the FastAPI WebSocket handler, which streams them to the browser. Using one system for both avoids adding a separate message broker (like RabbitMQ) and keeps the infrastructure simpler.

### Why perceptual fingerprinting on upload?

Perceptual hashing produces a content-based fingerprint that survives re-encoding. This enables duplicate detection (don't re-transcode the same video) and integrity checks on the assembled output.

## Monitoring

Grafana dashboard (http://localhost:3001, login: `admin` / `admin123` — local default only, change before any deployment) with 10 panels:

- Videos uploaded, jobs completed, jobs failed, emails sent
- Queue depth gauge, active workers, jobs in progress
- Backend memory usage
- Jobs per minute rate
- Job duration (p95) histogram

Custom Prometheus metrics:

- `videos_uploaded_total` — upload counter by status
- `transcoding_jobs_total` — job counter by quality and status
- `transcoding_queue_depth` — current queue size
- `active_workers` — number of RQ workers
- `transcoding_job_duration_seconds` — job duration histogram
- `emails_sent_total` — email counter by success/failure

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create new user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Get current user |

### Videos

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/upload` | Upload video file |
| GET | `/api/videos/list` | List user's videos |
| GET | `/api/videos/{id}/inspection` | Validation report |
| GET | `/api/videos/{id}/summary` | Transcoding summary |
| GET | `/api/videos/{id}/download/{quality}` | Download transcoded video |
| POST | `/api/videos/{id}/cancel` | Cancel transcoding |
| DELETE | `/api/videos/{id}` | Delete video and all versions |

### Admin (admin users only — others get 403)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/admin/stats` | System statistics |
| GET | `/api/admin/videos` | All videos (filterable) |
| GET | `/api/admin/jobs` | All jobs (filterable) |
| GET | `/api/admin/health` | Service health check |

### System

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| WS | `/ws/progress/{video_id}` | Real-time progress |

## Getting Started

### Prerequisites

- Docker & Docker Compose
- (Optional, for local dev) Python 3.11+, Node.js 18+, FFmpeg

### Run with Docker Compose

```bash
git clone https://github.com/BLESSEDEFEM/production-video-transcoding-pipeline.git
cd production-video-transcoding-pipeline
docker compose up -d --build
```

This starts all 8 services:

| Service | URL | Purpose |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js UI |
| Backend | http://localhost:8000 | FastAPI API |
| Grafana | http://localhost:3001 | Monitoring |
| Prometheus | http://localhost:9090 | Metrics |
| MinIO | http://localhost:9001 | Storage console |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Queue & pub/sub |

### Run Locally (Development)

```bash
# Backend
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
```

### Kubernetes Deployment (experimental — manifests not run in production)

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml

# Scale workers
kubectl scale deployment transcoding-worker -n video-app --replicas=8
```

## Deployment History

Ran on a single AWS EC2 instance (free tier) with Docker Compose for about 6 months; that instance is now decommissioned. It currently runs locally with `docker compose up -d --build`.

## Tests

```bash
cd backend
pip install pytest httpx==0.27.2
python -m pytest tests/test_api.py -v
```

25 tests covering: health endpoints, user auth, video upload/inspection/summary/cancellation, admin dashboard with filtering, admin-only access (non-admins get 403), and monitoring endpoints.

## Known Issues

- Chunk assembly can add a few frames at chunk boundaries, which lowers PSNR.
- A failed transcoding job returns an error instead of raising it, so RQ marks it successful and doesn't retry.
- The UI can show "Transcoding Complete" while some quality jobs are still running or have failed.
- The progress page doesn't show a message when a video is rejected.
- Each quality level re-downloads and re-splits the original (planned: split once, fan out).
- Several files in `tests/` are manual scripts, not pytest tests; the real suite is `tests/test_api.py`.

## Project Structure

```
production-video-transcoding-pipeline/
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
│   ├── tests/              # API test suite (test_api.py) + manual scripts
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js pages (login, upload, progress, admin)
│   ├── components/         # Shared React components
│   ├── Dockerfile
│   └── package.json
├── k8s/                    # Kubernetes manifests (experimental)
├── monitoring/
│   ├── prometheus.yml      # Scrape config
│   └── grafana/            # Dashboard provisioning
└── docker-compose.yml      # 8-service orchestration
```

## License

MIT
