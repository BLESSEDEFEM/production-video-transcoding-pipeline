import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage import minio_client
import os

bucket = os.getenv("MINIO_BUCKET", "videos")
object_name = "originals/1/test_video_haibit.mp4"

try:
    # Try to get object info
    stat = minio_client.stat_object(bucket, object_name)
    print(f"✅ File exists in MinIO!")
    print(f"   Bucket: {bucket}")
    print(f"   Path: {object_name}")
    print(f"   Size: {stat.size} bytes")
except Exception as e:
    print(f"❌ File NOT in MinIO: {e}")
    print(f"   Looking for: {bucket}/{object_name}")