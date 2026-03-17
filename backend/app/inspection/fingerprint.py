"""
Fingerprinting adapter for Day 3 compatibility
Wraps your existing VideoFingerprint class
"""
from typing import Dict
from pathlib import Path
from app.services.video_fingerprinting import VideoFingerprint

def generate_fingerprint(video_path: str, output_dir: str = None) -> Dict:
    """
    Generate video fingerprint
    
    Simple wrapper around your existing VideoFingerprint
    Returns format expected by Day 3
    
    Args:
        video_path: Path to video file
        output_dir: Optional directory for signature file
        
    Returns:
        dict with 'signature_hash', 'signature_file', metadata, etc.
    """
    # Use your existing fingerprinter
    fingerprinter = VideoFingerprint()
    
    # Generate signature file path
    if output_dir:
        sig_dir = Path(output_dir)
    else:
        sig_dir = Path("storage/signatures")
    
    sig_dir.mkdir(parents=True, exist_ok=True)
    signature_file = str(sig_dir / f"{Path(video_path).stem}.sig")
    
    # Generate fingerprint using your existing code
    result = fingerprinter.generate_fingerprint(video_path, signature_file)
    
    # Check for errors
    if 'error' in result:
        raise Exception(result['error'])
    
    # Extract resolution dimensions
    metadata = result.get('metadata', {})
    resolution_str = metadata.get('resolution', '0x0')
    
    # Parse width x height
    try:
        width, height = map(int, resolution_str.split('x'))
    except:
        width, height = 0, 0
    
    # Convert to Day 3 format
    return {
        'signature_hash': result['fingerprint_id'],
        'signature_file': result['signature_file'],
        'frame_count': metadata.get('frame_count', 0),
        'duration': metadata.get('duration', 0),
        'resolution': resolution_str,
        'width': width,
        'height': height,
        'codec': metadata.get('codec', 'unknown'),
        'fps': metadata.get('fps', 0)
    }

def compare_fingerprints(original_fp: Dict, transcoded_fp: Dict, threshold: float = 0.95) -> Dict:
    """
    Compare two fingerprints
    
    Args:
        original_fp: Original video fingerprint dict
        transcoded_fp: Transcoded video fingerprint dict
        threshold: Similarity threshold (0-1)
        
    Returns:
        dict with 'passed', 'similarity', 'frame_diff', etc.
    """
    fingerprinter = VideoFingerprint()
    
    # Get signature files
    sig1 = original_fp.get('signature_file')
    sig2 = transcoded_fp.get('signature_file')
    
    if not sig1 or not sig2:
        return {
            'passed': False,
            'error': 'Missing signature files'
        }
    
    # Compare using your existing code
    comparison = fingerprinter.compare_fingerprints(sig1, sig2, threshold)
    
    if 'error' in comparison:
        return {
            'passed': False,
            'error': comparison['error']
        }
    
    # Frame count comparison
    frame_diff = abs(
        original_fp.get('frame_count', 0) - transcoded_fp.get('frame_count', 0)
    )
    
    # Duration comparison
    duration_diff = abs(
        original_fp.get('duration', 0) - transcoded_fp.get('duration', 0)
    )
    
    return {
        'passed': comparison['is_match'],
        'similarity': comparison['similarity'],
        'frame_diff': frame_diff,
        'duration_diff': duration_diff,
        'match_quality': comparison['match_quality']
    }