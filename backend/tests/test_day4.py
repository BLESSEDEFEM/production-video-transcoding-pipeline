"""
Full Day 4 test — runs the entire chunked pipeline on a real video.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.video_splitter import split_video
from app.workers.parallel_processor import process_chunks_in_parallel
from app.services.chunk_assembler import assemble_chunks
from app.services.quality_metrics import QualityMetrics
import glob

# Find test video (a high-res video)
videos = glob.glob("../storage/uploads/*.mp4")
if not videos:
    print("❌ Upload a video first!")
    exit()

# Filter for videos > 720p
original_video = next((v for v in videos if '1080' in v or '4k' in v.lower()), videos[0])
print(f"\n{'='*60}")
print(f"DAY 4 FULL PIPELINE TEST")
print(f"{'='*60}")
print(f"Video: {original_video}")

# Step 1: Split
print(f"\n--- STEP 1: SPLIT ---")
chunks = split_video(original_video, num_chunks=4, output_dir="temp_chunks/day4_test")

# Step 2: Parallel transcode
print(f"\n--- STEP 2: PARALLEL TRANSCODE ---")
parallel_result = process_chunks_in_parallel(
    chunks=chunks,
    quality='720p',
    output_dir="temp_chunks/day4_test/transcoded"
)

print(f"\nChunk results:")
for r in parallel_result['results']:
    status = "✅" if r['success'] else "❌"
    print(f"  {status} Chunk {r['chunk_index']}: frames_match={r.get('frames_match')}, actual_frames={r.get('actual_frames')}")

# Step 3: Assemble
print(f"\n--- STEP 3: ASSEMBLE ---")
final_path = "temp_chunks/day4_test/final_720p.mp4"
assembled = assemble_chunks(parallel_result['results'], final_path)

# Step 4: Quality check
if assembled:
    print(f"\n--- STEP 4: QUALITY METRICS ---")
    from app.services.quality_metrics import QualityMetrics
    qm = QualityMetrics()
    
    # Convert Windows backslashes to forward slashes for FFmpeg
    original_normalized = str(Path(original_video).as_posix())
    final_normalized = str(Path(final_path).as_posix())
    
    print(f"Comparing: {original_normalized} vs {final_normalized}")
    
    quality = qm.compare_videos(
        original_normalized,   # ← Use normalized paths
        final_normalized,
        metrics=['psnr', 'ssim', 'vmaf']
    )
    
    # Extract scores
    psnr_score = quality['metrics']['psnr'].get('score', 0)
    ssim_score = quality['metrics']['ssim'].get('score', 0)
    vmaf_score = quality['metrics']['vmaf'].get('score', 0)
    
    
    print(f"\n{'='*60}")
    print(f"DAY 4 COMPLETE RESULTS:")
    print(f"{'='*60}")
    print(f"  Chunks processed: {parallel_result['success_count']}/{len(chunks)}")
    print(f"  Assembly: {'✅ Success' if assembled else '❌ Failed'}")
    print(f"\n📊 QUALITY METRICS:")
    print(f"  PSNR:  {psnr_score:.2f} dB ({quality['metrics']['psnr'].get('quality', 'N/A')})")
    print(f"  SSIM:  {ssim_score:.4f} ({quality['metrics']['ssim'].get('quality', 'N/A')})")
    
    # Include VMAF if it was calculated
    if 'vmaf' in quality['metrics'] and 'error' not in quality['metrics']['vmaf']:
        vmaf_score = quality['metrics']['vmaf'].get('score', 0)
        vmaf_quality = quality['metrics']['vmaf'].get('quality', 'N/A')
        print(f"  VMAF:  {vmaf_score:.2f} ({vmaf_quality})")
    
    # Overall pass/fail
    psnr_ok = psnr_score >= 30
    ssim_ok = ssim_score >= 0.85
    overall_pass = psnr_ok and ssim_ok
    
    print(f"\n  Overall: {'✅ PASSED' if overall_pass else '⚠️  CHECK NEEDED'}")
    print(f"{'='*60}")
else:
    print("❌ Assembly failed")