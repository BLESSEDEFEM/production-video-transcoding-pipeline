"""
Test video fingerprinting
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_fingerprinting import VideoFingerprint, SimplePerceptualHash


def test_fingerprinting(video1: str, video2: str):
    """Test fingerprint generation and comparison"""
    
    print("="*70)
    print("VIDEO FINGERPRINTING TEST")
    print("="*70)
    
    fp_service = VideoFingerprint()
    
    # Generate fingerprints
    print("\n📝 STEP 1: Generate Fingerprints")
    print("-"*70)
    
    fp1 = fp_service.generate_fingerprint(video1)
    if 'error' in fp1:
        print(f"❌ Error with video 1: {fp1['error']}")
        return
    
    fp2 = fp_service.generate_fingerprint(video2)
    if 'error' in fp2:
        print(f"❌ Error with video 2: {fp2['error']}")
        return
    
    # Compare
    print("\n📊 STEP 2: Compare Fingerprints")
    print("-"*70)
    
    comparison = fp_service.compare_fingerprints(
        fp1['signature_file'],
        fp2['signature_file'],
        threshold=0.90
    )
    
    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    
    print(f"\nVideo 1: {Path(video1).name}")
    print(f"  Fingerprint ID: {fp1['fingerprint_id']}")
    print(f"  File Hash: {fp1['file_hash']}")
    
    print(f"\nVideo 2: {Path(video2).name}")
    print(f"  Fingerprint ID: {fp2['fingerprint_id']}")
    print(f"  File Hash: {fp2['file_hash']}")
    
    print(f"\nComparison:")
    print(f"  Similarity: {comparison['similarity']*100:.2f}%")
    print(f"  Match: {'YES ✅' if comparison['is_match'] else 'NO ❌'}")
    print(f"  Quality: {comparison['match_quality']}")
    
    print("\n" + "="*70)
    
    # Show difference between file hash and fingerprint
    print("\n💡 KEY INSIGHT:")
    print("-"*70)
    
    file_hashes_match = fp1['file_hash'] == fp2['file_hash']
    fingerprints_match = comparison['is_match']
    
    print(f"File Hashes Match: {'YES' if file_hashes_match else 'NO'}")
    print(f"Fingerprints Match: {'YES' if fingerprints_match else 'NO'}")
    
    if not file_hashes_match and fingerprints_match:
        print("\n✨ This demonstrates the power of fingerprinting!")
        print("   Files are different, but content is the same!")
    elif file_hashes_match and fingerprints_match:
        print("\n📌 Files are identical (exact copies)")
    else:
        print("\n❌ Videos are different")
    
    print("="*70 + "\n")


def test_simple_hash(video_path: str):
    """Test simple perceptual hashing"""
    
    print("="*70)
    print("SIMPLE PERCEPTUAL HASH TEST")
    print("="*70)
    
    hasher = SimplePerceptualHash()
    result = hasher.generate_hash(video_path)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\nVideo: {Path(video_path).name}")
    print(f"Perceptual Hash: {result['perceptual_hash']}")
    print(f"Frames Analyzed: {result['frame_count']}")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Compare two videos:")
        print("    python test_fingerprinting.py video1.mp4 video2.mp4")
        print("\n  Or test single video:")
        print("    python test_fingerprinting.py video1.mp4 --simple")
        sys.exit(1)
    
    if sys.argv[2] == '--simple':
        test_simple_hash(sys.argv[1])
    else:
        test_fingerprinting(sys.argv[1], sys.argv[2])