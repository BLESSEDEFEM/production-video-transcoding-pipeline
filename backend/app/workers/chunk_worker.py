"""
Chunk Worker - transcodes ONE chunk and verifies it.
Multiple of these run in parallel.
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict

QUALITY_PRESETS = {
    '360p': {'resolution': '640x360', 'bitrate': '800k', 'audio_bitrate': '96k'},
    '480p': {'resolution': '854x480', 'bitrate': '1400k', 'audio_bitrate': '128k'},
    '720p': {'resolution': '1280x720', 'bitrate': '2800k', 'audio_bitrate': '128k'},
    '1080p': {'resolution': '1920x1080', 'bitrate': '5000k', 'audio_bitrate': '192k'}
}


def transcode_chunk(chunk_info: Dict, quality: str, output_dir: str) -> Dict:
    """
    Transcode ONE chunk to the target quality.
    
    chunk_info looks like:
        {
            "chunk_index": 2,
            "path": "temp_chunks/chunk_2.mp4",
            "expected_frames": 75,
            "duration": 2.5  
        }
        
    Returns:
        {
            "chunk-index": 2,
            "success": True,
            "output_path": "temp_chunks/chunk_2_720p.mp4",
            "actual_frames": 74,
            "frames_match": True,
            "error": None
        }
    """
    chunk_index = chunk_info['chunk_index']
    input_path = chunk_info['path']
    expected_frames = chunk_info['expected_frames']
    expected_duration = chunk_info['duration']
    
    output_path = str(Path(output_dir) / f"chunk_{chunk_index}_{quality}.mp4")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"   🎬 [Chunk {chunk_index}] Starting transcode to {quality}...")
    started_at = datetime.now(timezone.utc)
    
    try:
        # Step 1: Transcode
        _ffmpeg_transcode(input_path, output_path, quality)
        print(f"   ✅ [Chunk {chunk_index}] Transcoded")
        
        # Step 2: Verify - count actual frames and check duration
        actual_frames, actual_duration = _get_frame_count_and_duration(output_path)
        
        # Allow a small tolerance: +/- frames is normal due to keyframe alignment
        frames_match = abs(actual_frames - expected_frames) <= 5
        duration_ok = abs(actual_duration - expected_duration) <= 0.5
        
        completed_at = datetime.now(timezone.utc)
        processing_time = (completed_at - started_at).total_seconds()
        
        if frames_match:
            print(f"   ✅ [chunk {chunk_index}] Verified ({actual_frames} frames, {processing_time:.1f}s)")
        else:
            print(f"   ⚠️ [Chunk {chunk_index}] Frame mismatch: expected {expected_frames}, got {actual_frames}")
            
        return {
            "chunk_index": chunk_index,
            "success": True,
            "output_path": output_path,
            "expected_frames": expected_frames,
            "actual_frames": actual_frames,
            "frames_match": frames_match,
            "duration_ok": duration_ok,
            "processing_time": processing_time,
            "error": None
        }
        
    except Exception as e:
        print(f"   ❌ [Chunk {chunk_index}] Failed: {e}")
        return {
            "chunk_index": chunk_index,
            "success": False,
            "output_path": None,
            "frames_match": False,
            "error": str(e)
        }
        
        
def _ffmpeg_transcode(input_path: str, output_path: str, quality: str):
        """Run FFmpeg to transcode one chunk."""
        preset = QUALITY_PRESETS[quality]
        
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', f"scale={preset['resolution']}:force_original_aspect_ratio=decrease",
            '-c:v', 'libx264',
            '-b:v', preset['bitrate'],
            '-c:a', 'aac',
            '-b:a', preset['audio_bitrate'],
            '-preset', 'fast',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr[-300:]}")
        
        
def _get_frame_count_and_duration(video_path: str):
    """
    Count the actual frames in a video file.

    We use -count_frames which makes FFprobe count every single frame.
    It's slower but accurate.

    Returns: (frame_count, duration_in_seconds)
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        '-count_frames',  # this counts actual frames
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    data = json.loads(result.stdout)
    
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video':
            frame_count = int(stream.get('nb_read_frames', 0))
            duration = float(stream.get('duration', 0))
            return frame_count, duration
        
    return 0, 0.0