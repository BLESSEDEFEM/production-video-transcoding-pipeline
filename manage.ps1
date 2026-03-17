# manage.ps1 — shortcuts for common operations
# Usage: .\manage.ps1 <command>

param($command)

switch ($command) {
    "start" {
        Write-Host "Starting all services with Docker Compose..."
        docker-compose up --build -d
    }
    "stop" {
        Write-Host "Stopping all services..."
        docker-compose down
    }
    "logs" {
        docker-compose logs -f
    }
    "backend-logs" {
        docker-compose logs -f backend
    }
    "worker-logs" {
        docker-compose logs -f worker
    }
    "scale-workers" {
        param($n = 4)
        Write-Host "Scaling workers to $n..."
        kubectl scale deployment transcoding-worker --replicas=$n -n video-app
    }
    "k8s-status" {
        kubectl get pods -n video-app
    }
    "k8s-apply" {
        Write-Host "Applying all Kubernetes configs..."
        kubectl apply -f k8s/
    }
    "k8s-delete" {
        Write-Host "Deleting all Kubernetes resources..."
        kubectl delete namespace video-app
    }
    default {
        Write-Host "Available commands:"
        Write-Host "  start          - Start with Docker Compose"
        Write-Host "  stop           - Stop all services"
        Write-Host "  logs           - Show all logs"
        Write-Host "  backend-logs   - Show backend logs only"
        Write-Host "  worker-logs    - Show worker logs only"
        Write-Host "  k8s-status     - Show Kubernetes pod status"
        Write-Host "  k8s-apply      - Apply all Kubernetes configs"
        Write-Host "  k8s-delete     - Delete all Kubernetes resources"
    }
}