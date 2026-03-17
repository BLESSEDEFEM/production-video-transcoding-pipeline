"""
Test transcoding worker
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.transcoder import transcode_video

# Test with a real video ID from your database
# Replace 1 with actual video ID that exists
video_id = 11
quality = '720p'

print("="*70)
print("TESTING TRANSCODING WORKER")
print("="*70)
print(f"Video ID: {video_id}")
print(f"Quality: {quality}")
print("="*70)

try:
    result = transcode_video(video_id, quality)
    
    print("\n✅ WORKER TEST COMPLETED!")
    print(f"Result: {result}")
    
except Exception as e:
    print(f"\n❌ WORKER TEST FAILED!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()