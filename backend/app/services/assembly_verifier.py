"""
Assembly Verifier — after chunks are joined, check the final video is intact.

Questions it answers:
1. Is the file readable? (not corrupted)
2. Is the duration correct? (original ≈ final)
3. Is the frame count correct? (original ≈ final)
4. Are there any FFmpeg decode errors?
"""
import subprocess
import json
from pathlib import Path
from typing import Dict


def get_video_stats(video_path: str) -> Dict:
    """
    Get duration and frame count of a video using FFprobe.

    Returns:
        {"duration": 120.5, "frame_count": 3615, "readable": True}
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        '-count_frames',   # <- actually count frames (slower but accurate)
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return {"readable": False, "error": result.stderr[:200]}
        
        data = json.loads(result.stdout)
        
        duration = float(data.get('format', {}).get('duration', 0))
        frame_count = 0
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                frame_count = int(stream.get('nb_read_frames', 0))
                break
            
        return {
            "readable": True,
            "duration": round(duration, 3),
            "frame_count": frame_count
        }
        
    except Exception as e:
        return {"readable": False, "error": str(e)}
        

def check_for_decode_errors(video_path: str) -> Dict:
    """
    Ask FFmpeg to decode the entire video and report any errors.

    This catches invisible corruption — the file might look fine but
    have broken frames inside.

    FFmpeg decodes every frame and reports problems to stderr.
    We check if there are any error messages.

    Returns:
        {"clean": True, "error_count": 0, "errors": []}
    """
    cmd = [
        'ffmpeg',
        '-v', 'error',     # <- only report errors, no info spam
        '-i', video_path,
        '-f', 'null',      # <- don't save output, just decode
        '-'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # Any output in stderr = there were decode errors
    errors = [line for line in result.stderr.split('\n') if line.strip()]
    
    return {
        "clean": len(errors) == 0,
        "error_count": len(errors),
        "errors": errors[:5]   # show first 5 only
    }
    
    
def verify_assembly(
    original_path: str,
    assembled_path: str,
    duration_tolerance: float = 1.0,     # allow up to 1 second difference
    frame_tolerance: float = 0.02        # allow up to 2% frame difference
) -> Dict:
    """
    Full verification of the assembled video against the original.

    Checks:
    1. Assembled file exists and is readable
    2. Duration is close to original (within 1 second)
    3. Frame count is close to original (within 2%)
    4. No decode errors in assembled file

    Returns a full report dict.

    Example:
        {
            "passed": True,
            "duration_ok": True,
            "frames_ok": True,
            "decode_ok": True,
            "original_duration": 120.0,
            "original_duration": 120.0,
            "assembled_duration": 119.97,
            "original_frames": 3600,
            "assembled_frames": 3598,
            "details": "All checks passed"
        }
    """
    print(f"\n🔍 ASSEMBLY VERIFICATION")
    print(f"   Original:  {original_path}")
    print(f"   Assembled: {assembled_path}")
    
    report = {
        "passed": False,
        "duration_ok": False,
        "frames_ok": False,
        "decode_ok": False
    }
    
    # ── CHECK 1: FILE EXISTS ──
    if not Path(assembled_path).exists():
        report["details"] = "Assembled file does not exist"
        print(f"   ❌ File not found!")
        return report

    # ── CHECK 2: GET STATS FOR BOTH VIDEOS ──
    print(f"   📊 Reading original stats...")
    orig_stats = get_video_stats(original_path)

    print(f"   📊 Reading assembled stats...")
    asm_stats = get_video_stats(assembled_path)

    if not orig_stats.get('readable'):
        report["details"] = f"Cannot read original: {orig_stats.get('error')}"
        return report

    if not asm_stats.get('readable'):
        report["details"] = f"Cannot read assembled: {asm_stats.get('error')}"
        return report
    
    report["original_duration"] = orig_stats["duration"]
    report["assembled_duration"] = asm_stats["duration"]
    report["original_frames"] = orig_stats["frame_count"]
    report["assembled_frames"] = asm_stats["frame_count"]
    
    # ── CHECK 3: DURATION ──
    duration_diff = abs(orig_stats["duration"] - asm_stats["duration"])
    report["duration_diff"] = round(duration_diff, 3)
    report["duration_ok"] = duration_diff <= duration_tolerance

    print(f"   Duration: {orig_stats['duration']:.2f}s → {asm_stats['duration']:.2f}s "
          f"(diff: {duration_diff:.3f}s) {'✅' if report['duration_ok'] else '❌'}")
    
    
    # ── CHECK 4: FRAME COUNT ──
    # We expect transcoded video to have slightly different frame count
    # (re-encoding changes keyframe alignment)
    # So we allow 2% tolerance
    if orig_stats["frame_count"] > 0:
        frame_diff_ratio = abs(orig_stats["frame_count"] - asm_stats["frame_count"]) / orig_stats["frame_count"]
        report["frame_diff_ratio"] = round(frame_diff_ratio, 4)
        report["frames_ok"] = frame_diff_ratio <= frame_tolerance
    else:
        report["frames_ok"] = True  # can't compare if original has 0 frames
        report["frame_diff_ratio"] = 0

    print(f"   Frames: {orig_stats['frame_count']} → {asm_stats['frame_count']} "
          f"(diff: {report.get('frame_diff_ratio', 0)*100:.2f}%) {'✅' if report['frames_ok'] else '⚠️'}")
    
    # ── CHECK 5: DECODE ERRORS ──
    print(f"   🔎 Checking for decode errors...")
    decode_check = check_for_decode_errors(assembled_path)
    report["decode_ok"] = decode_check["clean"]
    report["decode_errors"] = decode_check["errors"]

    print(f"   Decode errors: {decode_check['error_count']} {'✅' if decode_check['clean'] else '⚠️'}")
    
    # ── OVERALL RESULT ──
    # Duration and decode MUST pass. Frames just warn (transcoding can shift them slightly).
    report["passed"] = report["duration_ok"] and report["decode_ok"]

    if report["passed"]:
        report["details"] = "Assembly verified ✅"
        print(f"\n   ✅ ASSEMBLY VERIFIED")
    else:
        issues = []
        if not report["duration_ok"]:
            issues.append(f"Duration off by {duration_diff:.2f}s")
        if not report["decode_ok"]:
            issues.append(f"{decode_check['error_count']} decode errors")
        report["details"] = " | ".join(issues)
        print(f"\n   ⚠️  Issues: {report['details']}")

    return report