# Deployment Guide

This guide covers deploying the Video Transcoding Pipeline from local development to production environments.

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|------------|
| Docker Compose | Local dev, demos, single server | Low |
| Kubernetes (Minikube) | Local K8s testing | Medium |
| Kubernetes (Cloud) | Production deployment | High |

## Option 1: Docker Compose (Single Server)

This is the simplest deployment. All 8 services run on one machine.

### Prerequisites

- A Linux server (Ubuntu 22.04+ recommended) with at least 4GB RAM and 2 CPUs
- Docker and Docker Compose installed
- Git installed

### Steps
```bash
# 1. Clone the repository
git clone https://github.com/yourusername/video-transcoding-pipeline.git
cd video-transcoding-pipeline

# 2. Create environment file
cp backend/.env.example backend/.env
# Edit backend/.env with your production values

# 3. Update docker-compose.yml
# Change these default passwords:
#   - POSTGRES_PASSWORD
#   - GF_SECURITY_ADMIN_PASSWORD
#   - SECRET_KEY
#   - MINIO_ROOT_USER / MINIO_ROOT_PASSWORD

# 4. Build and start all services
docker compose build
docker compose up -d

# 5. Verify everything is running
docker compose ps

# 6. Check logs for errors
docker compose logs backend --tail 50
docker compose logs worker --tail 50
```

### Scaling Workers

To process more videos simultaneously, scale the worker service:
```bash
# Run 4 workers instead of 1
docker compose up -d --scale worker=4

# Check all workers are running
docker compose ps
```

### Updating the Application
```bash
# Pull latest code
git pull origin main

# Rebuild only changed services
docker compose build backend worker frontend

# Restart with zero downtime
docker compose up -d
```

## Option 2: Kubernetes (Minikube for Local Testing)

### Prerequisites

- Minikube installed
- kubectl installed
- Docker installed

### Steps
```bash
# 1. Start Minikube
minikube start --cpus=4 --memory=4096

# 2. Use Minikube's Docker daemon (so K8s can find our images)
eval $(minikube docker-env)

# 3. Build images inside Minikube's Docker
docker build -t video-backend:latest ./backend -f ./backend/Dockerfile
docker build -t video-worker:latest ./backend -f ./backend/Dockerfile.worker
docker build -t video-frontend:latest ./frontend -f ./frontend/Dockerfile

# 4. Apply Kubernetes manifests (order matters)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/worker.yaml

# 5. Check pod status
kubectl get pods -n video-app

# 6. Access the backend (Minikube tunneling)
minikube service backend-service -n video-app
```

### Scaling Workers in Kubernetes
```bash
# Scale up for heavy load
kubectl scale deployment transcoding-worker -n video-app --replicas=8

# Scale down when idle
kubectl scale deployment transcoding-worker -n video-app --replicas=1

# Check worker pods
kubectl get pods -n video-app -l app=transcoding-worker
```

### Monitoring Pods
```bash
# View logs for a specific worker
kubectl logs -n video-app deployment/transcoding-worker --tail=50

# View logs for the backend
kubectl logs -n video-app deployment/backend --tail=50

# Describe a pod (useful for debugging startup failures)
kubectl describe pod -n video-app <pod-name>
```

## Option 3: Cloud Kubernetes (Production)

For a real production deployment on AWS EKS, Google GKE, or Azure AKS.

### Architecture Changes for Production

| Component | Development | Production |
|-----------|-------------|------------|
| Database | PostgreSQL container | AWS RDS / Cloud SQL |
| Cache/Queue | Redis container | AWS ElastiCache / Memorystore |
| Storage | MinIO container | AWS S3 / Cloud Storage |
| Monitoring | Grafana container | Grafana Cloud / Datadog |
| Email | Console logging | SendGrid / AWS SES |
| SSL | None | Let's Encrypt / ACM |

### Key Steps

1. **Container Registry**: Push images to ECR, GCR, or Docker Hub
```bash
# Example: Docker Hub
docker build -t yourusername/video-backend:v1.0 ./backend
docker push yourusername/video-backend:v1.0
```

2. **Update K8s Manifests**: Change `imagePullPolicy: Never` to `Always` and update image names to point to your registry

3. **External Services**: Update environment variables to point to managed services
```yaml
# Example: Using AWS RDS instead of PostgreSQL container
env:
  - name: DATABASE_URL
    value: "postgresql://user:pass@your-rds-instance.region.rds.amazonaws.com:5432/video_transcoding"
```

4. **Ingress Controller**: Set up NGINX Ingress or AWS ALB for external access with HTTPS

5. **Secrets Management**: Use Kubernetes Secrets or AWS Secrets Manager instead of plain environment variables

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | — | PostgreSQL connection string |
| REDIS_URL | Yes | — | Redis connection string |
| MINIO_ENDPOINT | Yes | — | MinIO/S3 endpoint |
| MINIO_ACCESS_KEY | Yes | — | MinIO/S3 access key |
| MINIO_SECRET_KEY | Yes | — | MinIO/S3 secret key |
| MINIO_BUCKET | Yes | videos | Storage bucket name |
| SECRET_KEY | Yes | — | JWT signing key (use a long random string) |
| ALGORITHM | No | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | No | 30 | Token expiry time |
| SENDGRID_API_KEY | No | — | SendGrid API key for emails |
| SMTP_HOST | No | — | SMTP server hostname |
| SMTP_PORT | No | 587 | SMTP server port |
| SMTP_USER | No | — | SMTP username |
| SMTP_PASSWORD | No | — | SMTP password |
| FROM_EMAIL | No | noreply@videotranscoder.local | Sender email address |

## Health Checks

Use these endpoints to verify the deployment is working:
```bash
# Backend API health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "video-transcoding-backend", "version": "1.0.0"}

# Prometheus metrics
curl http://localhost:8000/metrics
# Expected: Prometheus text format with custom metrics

# Admin health (requires auth token)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/admin/health
# Expected: {"overall": "healthy", "services": {"database": ..., "redis": ..., "minio": ...}}
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker compose logs backend --tail 100

# Common issues:
# - DATABASE_URL wrong → "connection refused" error
# - Redis not ready → backend starts before Redis, restart it
# - MinIO not ready → "Connection refused" on upload
```

### Worker not processing jobs
```bash
# Check worker logs
docker compose logs worker --tail 100

# Check Redis queue
docker compose exec redis redis-cli LLEN rq:queue:transcoding
# Should show number of pending jobs

# Check worker registration
docker compose exec redis redis-cli SMEMBERS rq:workers
# Should show at least one worker
```

### Videos stuck in "uploaded" status

The background validation task may have failed silently:
```bash
# Check backend logs for inspection errors
docker compose logs backend | grep -i "inspection\|error\|failed"

# Verify FFmpeg is installed in the backend container
docker compose exec backend ffmpeg -version
```

### Grafana shows no data
```bash
# Verify Prometheus is scraping the backend
curl http://localhost:9090/api/v1/targets
# The "video-backend" target should show state: "up"

# Verify backend metrics endpoint
curl http://localhost:8000/metrics
# Should show custom metrics like transcoding_queue_depth
```

### Out of disk space

Video files can fill up disk quickly:
```bash
# Check MinIO storage usage
docker compose exec minio du -sh /data

# Clean up old transcoded files via the admin API or MinIO console
# MinIO console: http://localhost:9001
```