"""
Test complete pipeline: Upload → Validate → Transcode multiple qualities
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.workers.transcoder import transcode_video

print("="*70)
print("DAY 3: FULL PIPELINE TEST")
print("="*70)

# Use existing approved video from database
video_id = 16  # Change to your approved video ID
qualities = ['360p', '480p', '720p', '1080p']

print(f"\nTranscoding video {video_id} to {len(qualities)} qualities...\n")

results = []

for quality in qualities:
    print(f"\n{'='*70}")
    print(f"TRANSCODING: {quality}")
    print(f"{'='*70}")
    
    try:
        result = transcode_video(video_id, quality)
        results.append({
            'quality': quality,
            'success': result.get('success', False),
            'job_id': result.get('job_id')
        })
        print(f"\n✅ {quality} completed!")
    except Exception as e:
        print(f"\n❌ {quality} failed: {e}")
        results.append({
            'quality': quality,
            'success': False,
            'error': str(e)
        })

print(f"\n{'='*70}")
print("PIPELINE TEST COMPLETE")
print(f"{'='*70}")

success_count = sum(1 for r in results if r['success'])
print(f"\nResults: {success_count}/{len(qualities)} successful")

for r in results:
    status = '✅' if r['success'] else '❌'
    print(f"  {status} {r['quality']}")

print(f"\n{'='*70}\n")