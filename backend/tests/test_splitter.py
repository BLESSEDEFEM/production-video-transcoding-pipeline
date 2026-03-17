import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_splitter import split_video, get_video_duration
import glob

# Find any video in storage/uploads
videos = glob.glob("../storage/uploads/*.mp4")
if not videos:
    print("❌ No videos found in ../storage/uploads/")
    print("   Upload a video via the frontend first, then run this test.")
    exit()

video_path = videos[0]
print(f"Testing with: {video_path}")

duration = get_video_duration(video_path)
print(f"Duration: {duration:.2f}s")

chunks = split_video(
    video_path=video_path,
    num_chunks=4,
    output_dir="temp_chunks/test"
)

print(f"\n📋 Result: {len(chunks)} chunks")
for c in chunks:
    print(f"  Chunk {c['chunk_index']}: {c['start_time']}s → {c['end_time']}s  ({c['expected_frames']} frames)")
    print(f"    File: {c['path']}")
    print(f"    Exists: {Path(c['path']).exists()}")