"""
Test frame-level analysis
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.inspection.metadata import MetadataExtractor
from app.inspection.frame_analyzer import FrameAnalyzer, FastFrameAnalyzer


def test_frame_analysis(video_path: str, fast: bool = False):
    """Test frame analysis"""
    
    print("="*70)
    print("FRAME-LEVEL ANALYSIS TEST")
    print("="*70)
    
    # Step 1: Get video info
    print("\n📊 STEP 1: Extract Video Info")
    print("-"*70)
    
    extractor = MetadataExtractor()
    metadata = extractor.extract(video_path)
    
    if 'error' in metadata:
        print(f"❌ Error: {metadata['error']}")
        return
    
    duration = metadata['file']['duration']
    fps = metadata['video']['fps'] if metadata['video'] else 30.0
    
    print(f"Duration: {duration:.2f}s")
    print(f"FPS: {fps:.2f}")
    
    # Step 2: Analyze frames
    print("\n🔍 STEP 2: Analyze Frames")
    print("-"*70)
    
    if fast:
        analyzer = FastFrameAnalyzer(sample_rate=10)
        print("Using FAST analyzer (sampling)")
    else:
        analyzer = FrameAnalyzer()
        print("Using FULL analyzer (comprehensive)")
    
    analysis = analyzer.analyze_frames(video_path, duration, fps)
    
    # Step 3: Report
    print("\n📋 STEP 3: Results")
    print("-"*70)
    
    if analysis['passed']:
        print("\n✅ FRAME ANALYSIS PASSED")
        print("   Video has acceptable frame quality")
    else:
        print("\n❌ FRAME ANALYSIS FAILED")
        
        black = analysis['black_frames']
        frozen = analysis['frozen_frames']
        
        if not black['passed']:
            print(f"   • Too many black frames: {black['percentage']:.2f}% (limit: {analyzer.MAX_BLACK_PERCENT}%)")
        
        if not frozen['passed']:
            print(f"   • Too many frozen frames: {frozen['percentage']:.2f}% (limit: {analyzer.MAX_FROZEN_PERCENT}%)")
    
    print("\n" + "="*70 + "\n")


def create_test_videos():
    """Create test videos with issues"""
    import subprocess
    
    print("Creating test videos...")
    
    # Video with black frames
    print("\n1. Creating video with black frames...")
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=10:size=1280x720:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=10',
        '-vf', "drawbox=enable='between(t,3,4)':x=0:y=0:w=iw:h=ih:color=black:t=fill",
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        'storage/uploads/test_black_frames.mp4'
    ]
    subprocess.run(cmd, capture_output=True)
    print("   ✅ Created: test_black_frames.mp4")
    
    # Normal video (no issues)
    print("\n2. Creating normal video...")
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', 'testsrc=duration=10:size=1280x720:rate=30',
        '-f', 'lavfi',
        '-i', 'sine=frequency=1000:duration=10',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        'storage/uploads/test_normal.mp4'
    ]
    subprocess.run(cmd, capture_output=True)
    print("   ✅ Created: test_normal.mp4")
    
    print("\n✅ Test videos created!\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Test video:")
        print("    python test_frame_analysis.py <video_path>")
        print("    python test_frame_analysis.py <video_path> --fast")
        print("\n  Create test videos:")
        print("    python test_frame_analysis.py --create-tests")
        sys.exit(1)
    
    if sys.argv[1] == '--create-tests':
        create_test_videos()
    else:
        fast_mode = '--fast' in sys.argv
        test_frame_analysis(sys.argv[1], fast=fast_mode)