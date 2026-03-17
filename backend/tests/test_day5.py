"""
Day 5 test — runs chunked transcoding with WebSocket updates.
Manually calls transcode_video_chunked() and watches the output.
"""
import sys
from pathlib import Path
import asyncio
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.chunked_transcoder import transcode_video_chunked

async def main():
    # Use the video_id that already exists in your database
    # (from Day 3 testing — video id 16 or whichever was approved)
    video_id = int(input("Enter video_id to transcode (e.g. 16): "))
    quality = input("Enter quality (360p/480p/720p/1080p) [default: 360p]: ").strip() or "360p"

    print(f"\n🚀 Starting chunked transcode: video_id={video_id}, quality={quality}")
    print("(Open browser at http://localhost:3000/progress?video_id={} to watch live)".format(video_id))
    print()

    result = await transcode_video_chunked(
        video_id=video_id,
        quality=quality,
        num_chunks=4
    )

    print(f"\n{'='*60}")
    print(f"RESULT: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
    if not result['success']:
        print(f"Error: {result.get('error')}")
    print(f"{'='*60}")

asyncio.run(main())