"""
MinIO storage client
Import from setup_minio.py
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import the client from setup_minio.py
from setup_minio import client as minio_client

# Re-export for app.storage import
__all__ = ['minio_client']