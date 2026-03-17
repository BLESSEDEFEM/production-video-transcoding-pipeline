from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv

load_dotenv()

# MinIO connection
client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False # No HTTPs in development
)

# Buckets to create
buckets = ["videos", "inspection-reports", "quality-reports"]

def setup_buckets():
    """Creates MinIO buckets if they don't exist"""
    for bucket in buckets:
        try:
            # Check if bucket exists already
            if not client.bucket_exists(bucket):
                # Create bucket
                client.make_bucket(bucket)
                print(f"Bucket '{bucket}'created")
            else:
                print(f"Bucket '{bucket}'exists already")
        except S3Error as e:
            print(f"Error with bucket '{bucket}': {e}")
            
if __name__ == "__main__":
    print(f"Setting up MinIO buckets...")
    setup_buckets()
    print(f"\n, MinIO setup complete!")