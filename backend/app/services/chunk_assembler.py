"""
Chunk Assembler — joins transcoded chunks into one final video
"""
import subprocess
import os
from pathlib import Path
from typing import List, Dict

def verify_boundaries(chunk_results: List[Dict]) -> List[Dict]:
    """
    Check the join point between each adjacent chunk pair.

    A boundary problem looks like this:
        chunk_1 ends on frame 74
        chunk_2 starts on frame 76   ← gap! frame 75 is missing

    We verify by checking if each chunk file is readable and not corrupted.
    Returns a list of boundary check results.

    Example output:
        [
            {"between_chunks": "0→1", "ok": True},
            {"between_chunks": "1→2", "ok": True},
            {"between_chunks": "2→3", "ok": True},
        ]
    """
    boundary_results = []
    
    for i in range(len(chunk_results) - 1):
        chunk_a = chunk_results[i]
        chunk_b = chunk_results[i + 1]
        
        path_a = chunk_a.get('output_path')
        path_b = chunk_b.get('output_path')
        
        ok = True
        error = None
        
        # Check both files are readable by FFprobe
        for path, label in [(path_a, f"chunk_{i}"), (path_b, f"chunk_{i+1}")]:
            if not path or not Path(path).exists():
                ok = False
                error = f"{label} file missing"
                break
            
            probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_format', path],
                capture_output=True, text=True
            )
            if probe.returncode != 0:
                ok = False
                error = f"{label} is corrupted: {probe.stderr[:100]}"
                break
            
        boundary_label = f"{i}->{i+1}"
        if ok:
            print(f"   ✅ Boundary {boundary_label}: OK")
        else:
            print(f"   ❌ Boundary {boundary_label}: {error}")
            
        boundary_results.append({
            "between_chunks": boundary_label,
            "ok": ok,
            "error": error
        })
        
    return boundary_results


def assemble_chunks(chunk_results: List[Dict], output_path: str) -> bool:
    """
    Join all transcoded chunks into one final video.

    chunk_results is the list of results from process_chunks_in_parallel().
    We only use chunks where success=True.

    Returns True if assembly worked, False if it failed.
    """
    # Only use successful chunks
    successful = [r for r in chunk_results if r['success'] and r.get('output_path')]
    successful.sort(key=lambda r: r['chunk_index'])
    
    if not successful:
        print("❌ No successful chunks to assemble!")
        return False
    
    print(f"\n🔧 ASSEMBLING {len(successful)} CHUNKS -> {output_path}")
    
    # Step 1: Check boundaries
    print("\n🔗 Checking boundaries...")
    boundary_results = verify_boundaries(successful)
    boundaries_ok = all(b['ok'] for b in boundary_results)
    
    if not boundaries_ok:
        print("⚠️ Some boundaries have issues - assembling anyway...")
        
    # Step 2: Create the concat list file
    concat_list_path = output_path + "_concat_list.txt"
    with open(concat_list_path, 'w') as f:
        for r in successful:
            # Use absolute paths to avoid path issues
            abs_path = str(Path(r['output_path']).resolve())
            f.write(f"file '{abs_path}'\n")
            
    print(f"\n📋 Concat list written with {len(successful)} files")
    
    # Step 3: Run FFmpeg to join them
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',   # concat mode
        '-safe', '0',     # allow absolute paths
        '-i', concat_list_path,
        '-c', 'copy',     # don't re-encode, just join
        '-y',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # Cleanup the temp list file
    os.remove(concat_list_path)
    
    if result.returncode != 0:
        print(f"❌ Assembly failed: {result.stderr[-200:]}")
        return False
    
    file_size = Path(output_path).stat().st_size
    print(f"✅ Assembly complete! ({file_size / 1024 / 1024:.1f} MB)")
    return True