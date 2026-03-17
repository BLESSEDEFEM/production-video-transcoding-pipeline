import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_splitter import split_video
from app.workers.parallel_processor import process_chunks_in_parallel
import glob

videos = glob.glob("../storage/uploads/*.mp4")
if not videos:
    print("❌ Upload a video first!")
    exit()

video_path = videos[0]
print(f"Testing with: {video_path}")

# Split into 4 chunks
chunks = split_video(video_path, num_chunks=4, output_dir="temp_chunks/parallel_test")

# Process all 4 simultaneously
result = process_chunks_in_parallel(
    chunks=chunks,
    quality='360p',
    output_dir="temp_chunks/parallel_test/transcoded"
)

print(f"\n📋 RESULTS:")
for r in result['results']:
    status = "✅" if r['success'] else "❌"
    print(f"  {status} Chunk {r['chunk_index']}: {r.get('actual_frames', '?')} frames, frames_match={r.get('frames_match')}")

print(f"\nAll passed: {result['all_passed']}")