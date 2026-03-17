"""
Video Splitter - cuts a video into equal_sized chunks
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict


def get_video_duration(video_path: str) -> float:
    """
    Ask FFprobe: how long is this video in seconds?
    
    Example:
        get_video_duration("video.mp4") -> 120.5 (means 2 minutes and 0.5 seconds)
    """
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    duration = float(data['format']['duration'])
    return duration

def split_video(video_path: str, num_chunks: int, output_dir: str) -> List[Dict]:
    """
    Cut a video into num_chunks equal pieces.
    
    Example:
        video is 120 seconds, num_chunks=4
        → chunk 0: 0s to 30s    (saved as chunk_0.mp4)
        → chunk 1: 30s to 60s   (saved as chunk_1.mp4)
        → chunk 2: 60s to 90s   (saved as chunk_2.mp4)
        → chunk 3: 90s to 120s  (saved as chunk_3.mp4)
        
    Returns a list of dicts, one per chunk:
        [
            {"chunk_index": 0, "start": 0, "end": 30, "duration": 30, "path": "chunk_0.mp4", "expected_frames": 900},
            {"chunk_index": 1, "start": 30, "end": 60, "duration": 30, "path": "chunk_1.mp4", "expected_frames": 900},
            ...
        ]
    """
    print(f"\n✂️  SPLITTING VIDEO INTO {num_chunks} CHUNKS")
    print(f"    Input: {video_path}")
    print(f"    Output dir: {output_dir}")
    
    # Create output folder
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Step 1: Get total duration
    duration = get_video_duration(video_path)
    chunk_duration = duration / num_chunks
    
    print(f"   Total duration: {duration:.2f}s")
    print(f"   Each chunk: {chunk_duration:.2f}s")
    
    # Step 2: Get FPS so we can calculate expected_frames per chunk
    fps = _get_fps(video_path)
    
    chunks = []
    
    # Step 3: Cut each chunk
    for i in range(num_chunks):
        start = i * chunk_duration
        # Last chunk goes to the very end to avoid rounding erros
        end = duration if i == num_chunks - 1 else (i + 1) * chunk_duration
        actual_duration = end - start
        expected_frames = int(actual_duration * fps)
        
        chunk_path = str(Path(output_dir) / f"chunk_{i}.mp4")
        
        print(f"\n   ✂️  Chunk {i}: {start:.2f}s -> {end:.2f}s ({expected_frames} frames)")
        
        # FFmpeg command to cut this chunk:
        # -ss = start position
        # -i  = input file
        # -t  = how many seconds to take
        # -c copy = don't re-encode (just cut — very fast!)
        cmd = [
            'ffmpeg',
            '-ss', str(start),
            '-i', video_path,
            '-t', str(actual_duration),
            '-c', 'copy',
            '-y',
            chunk_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed cutting chunk {i}: {result.stderr[-200:]}")
        
        print(f"   ✅ Chunk {i} saved: {chunk_path}")
        
        chunks.append({
            "chunk_index": i,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "duration": round(actual_duration, 3),
            "path": chunk_path,
            "expected_frames": expected_frames
        })
        
    print(f"\n✅ Split complete! {len(chunks)} chunks created.")
    return chunks


def _get_fps(video_path: str) -> float:
    """
    Get frames per second from a video.
    
    FFprobe returns fps as a fraction like "30/1" or "24000/1001".
    We convert it to a decimal: "30/1" -> 30.0
    """
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_streams',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video':
            fps_str = stream.get('r_frame_rate', '30/1')
            num, den = map(int, fps_str.split('/'))
            return round(num / den, 3) if den > 0 else 30.0
        
    return 30.0 # fallback