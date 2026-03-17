import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_fingerprinting import VideoFingerprint
from pathlib import Path

# Create fingerprint generator
fp = VideoFingerprint()

# Test with your video
# Get video path from command line
if len(sys.argv) < 2:
    print("Usage: python test2_fingerprinting.py <video_path>")
    sys.exit(1)

video_path = sys.argv[1]  # Change to your video

print("="*70)
print("TESTING ENHANCED FINGERPRINT GENERATION")
print("="*70)

result = fp.generate_fingerprint(video_path)

if 'error' not in result:
    print("\n📊 RESULTS:")
    print(f"   Fingerprint ID: {result['fingerprint_id']}")
    print(f"   Signature Size: {result['signature_size']} bytes")
    print(f"\n📹 VIDEO METADATA:")
    meta = result['metadata']
    print(f"   Resolution: {meta['resolution']}")
    print(f"   FPS: {meta['fps']}")
    print(f"   Duration: {meta['duration']:.2f}s")
    print(f"   Frames: {meta['frame_count']}")
    print(f"   Codec: {meta['codec']}")
else:
    print(f"\n❌ Error: {result['error']}")