"""
Video Fingerprinting Service
Creates perceptual fingerprints for duplicate detection
"""
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Tuple
import struct


class VideoFingerprint:
    """
    Video fingerprinting using FFmpeg signature filter
    """
    
    def __init__(self):
        pass
    
    def generate_fingerprint(
        self,
        video_path: str,
        signature_file: Optional[str] = None
    ) -> Dict:
        """
        Generate video fingerprint
        
        Args:
            video_path: Path to video file
            signature_file: Optional path to save signature
            
        Returns:
            Dictionary with fingerprint data
        """
        video_path = Path(video_path)
        
        if not signature_file:
            # Use absolute path to ensure we know where it goes
            sig_dir = Path("storage/signatures")
            sig_dir.mkdir(parents=True, exist_ok=True)
            signature_file = str(sig_dir / f"{video_path.stem}.sig")
            
        print(f"\n🔍 Generating fingerprint for: {video_path.name}")
        
        try:
            # Generate signature using FFmpeg
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', f'signature=filename={signature_file}:format=binary',
                '-an',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            print(f"   FFmpeg completed")
            
            # Check if signature file was created
            if not Path(signature_file).exists():
                mangled_name = signature_file.replace('\\', '').replace('/', '')
                if Path(mangled_name).exists():
                    signature_file = mangled_name
                else:
                    return {
                        'error': 'Signature file not created',
                        'details': result.stderr
                    }
            
            # Get file info
            file_size = video_path.stat().st_size
            sig_size = Path(signature_file).stat().st_size
            
            # Calculate file hash (for comparison)
            file_hash = self._calculate_file_hash(video_path)
            
            # Create fingerprint ID
            fingerprint_id = self._create_fingerprint_id(signature_file)

            # Get video metadata with FFprobe
            metadata = self._get_video_metadata(video_path)

            print(f"✅ Fingerprint generated")
            print(f"   ID: {fingerprint_id}")
            print(f"   Signature size: {sig_size} bytes")
            print(f"   Video: {metadata['resolution']} @ {metadata['fps']} fps")
            print(f"   Duration: {metadata['duration']:.2f}s")
            print(f"   Frames: {metadata['frame_count']}")

            return {
                'video_path': str(video_path),
                'video_size': file_size,
                'signature_file': signature_file,
                'signature_size': sig_size,
                'fingerprint_id': fingerprint_id,
                'file_hash': file_hash,
                'algorithm': 'ffmpeg_signature',
                # NEW: Add video metadata
                'metadata': {
                    'resolution': metadata['resolution'],
                    'width': metadata['width'],
                    'height': metadata['height'],
                    'fps': metadata['fps'],
                    'duration': metadata['duration'],
                    'frame_count': metadata['frame_count'],
                    'codec': metadata['codec']
                }
            }
            
        except subprocess.TimeoutExpired:
            return {'error': 'Fingerprint generation timed out'}
        except Exception as e:
            return {'error': f'Error generating fingerprint: {str(e)}'}
        
    def compare_fingerprints(
        self,
        sig_file1: str,
        sig_file2: str,
        threshold: float = 0.90,
    ) -> Dict:
        """
        Compares two video signatures
        
        Args:
            sig_file1: First signature file
            sig_file2: Second signature file
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            Comparison results
        """
        print(f"\n🔍 Comparing fingerprints:")
        print(f"   File 1: {Path(sig_file1).name}")
        print(f"   File 2: {Path(sig_file2).name}")
        
        try:
            # Read both signature files
            sig1_data = self._read_signature(sig_file1)
            sig2_data = self._read_signature(sig_file2)
            
            if not sig1_data or not sig2_data:
                return {'error': 'Could not read signature files'}
            
            # Calculate similarity
            similarity = self._calculate_similarity(sig1_data, sig2_data)
            
            # Determine if match
            is_match = similarity >= threshold
            
            result = {
                'signature_1': sig_file1,
                'signature_2': sig_file2,
                'similarity': round(similarity, 4),
                'threshold': threshold,
                'is_match': is_match,
                'match_quality': self._interpret_similarity(similarity)
            }
            
            print(f"\n📊 Comparison Results:")
            print(f"   Similarity: {similarity*100:.2f}%")
            print(f"   Threshold: {threshold*100:.2f}%")
            print(f"   Match: {'YES ✅'if is_match else 'NO ❌'}")
            print(f"   Quality: {result['match_quality']}")
            
            return result
        
        except Exception as e:
            return {'error': f'Error comparing fingerprints: {str(e)}'}
        
    def find_duplicates(
        self,
        video_path: str,
        database_signatures: list,
        threshold: float = 0.90
    ) -> list:
        """
        find duplicate videos in database
        
        Args:
            video_path: Path to video to check
            database_signatures: List of signature files to compare against
            threshold: Similarity threshold
            
        Returns:
            List of matches
        """
        print(f"\n🔍 Searching for duplicates of: {Path(video_path).name}")
        print(f"   Database size: {len(database_signatures)} videos")
        
        # Generate fingerprint for input video
        fp_result = self.generate_fingerprint(video_path)
        
        if 'error' in fp_result:
            return []
        
        input_sig = fp_result['signature_file']
        matches = []
        
        # Compare against all database signatures
        for i, db_sig in enumerate(database_signatures, 1):
            print(f"\r   Checking {i}/{len(database_signatures)}...", end='', flush=True)
            
            comparison = self.compare_fingerprints(
                input_sig,
                db_sig,
                threshold
            )
            
            if comparison.get('is_match'):
                matches.append({
                    'database_video': db_sig,
                    'similarity': comparison['similarity'],
                    'match_quality': comparison['match_quality']
                })
                
        print(f"\n\n✅ Search complete")
        print(f"   Found: {len(matches)} duplicate(s)")
        
        return matches
    
    # Helper methods
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file"""
        hasher = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
                
        return hasher.hexdigest()
    
    def _create_fingerprint_id(self, signature_file: str) -> str:
        """create unique fingerprint ID from signature"""
        with open(signature_file, 'rb') as f:
            sig_data = f.read()
            
        # Hash the signature to create compact ID
        hasher = hashlib.sha256()
        hasher.update(sig_data)
        
        return hasher.hexdigest()[:16] # Use first 16 chars
    
    def _read_signature(self, sig_file: str) -> Optional[bytes]:
        """Read signature file"""
        try:
            with open(sig_file, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading signature: {e}")
            return None
        
    def _calculate_similarity(self, sig1: bytes, sig2: bytes) -> float:
        """
        Calculate similarity between two signatures
        
        This is a simplified comparison.
        In production, use proper signature comparison algorithm.
        """
        # Ensure same length (pad shorter one)
        max_len = max(len(sig1), len(sig2))
        sig1_padded = sig1 + b'\x00' * (max_len - len(sig1))
        sig2_padded = sig2 + b'\x00' * (max_len - len(sig2))
        
        # Count matching bytes
        matches = sum(b1 == b2 for b1, b2 in zip(sig1_padded, sig2_padded))
        
        # Calculate similarity ratio
        similarity = matches / max_len if max_len > 0 else 0.0
        
        return similarity
    
    def _interpret_similarity(self, similarity: float) -> str:
        """Interpret similarity score"""
        if similarity >= 0.98:
            return "Identical (likely exact copy)"
        elif similarity >= 0.95:
            return "Very High (minor encoding differences)"
        elif similarity >= 0.90:
            return "High (Same content, different quality)"
        elif similarity >= 0.80:
            return "Medium (similar content with edits)"
        elif similarity >= 0.60:
            return "Low (partially similar)"
        else:
            return "Very low (different content)"
        
    def _get_video_metadata(self, video_path: Path) -> Dict:
        """
        Extract video metadata using FFprobe
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return self._default_metadata()
            
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = next(
                (s for s in data['streams'] if s['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                return self._default_metadata()
            
            # Extract metadata
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            # Calculate FPS
            fps_str = video_stream.get('r_frame_rate', '0/1')
            num, den = map(int, fps_str.split('/'))
            fps = num / den if den > 0 else 0
            
            return {
                'resolution': f"{width}x{height}",
                'width': width,
                'height': height,
                'fps': round(fps, 2),
                'duration': float(data['format'].get('duration', 0)),
                'frame_count': int(video_stream.get('nb_frames', 0)),
                'codec': video_stream.get('codec_name', 'unknown')
            }
            
        except Exception as e:
            print(f"   ⚠️  Could not extract metadata: {e}")
            return self._default_metadata()

    def _default_metadata(self) -> Dict:
        """Return default metadata when extraction fails"""
        return {
            'resolution': 'unknown',
            'width': 0,
            'height': 0,
            'fps': 0,
            'duration': 0,
            'frame_count': 0,
            'codec': 'unknown'
        }


class SimplePerceptualHash:
    """
    Simplified perceptual hashing for videos
    Alternative to FFmpeg signature (faster but less accurate)
    """
    
    def __init__(self):
        pass
    
    def generate_hash(self, video_path: str) -> Dict:
        """
        Generate simple perceptual hash
        Based on sampling key frames
        """
        print(f"\n🔍 Generating perceptual hash for: {Path(video_path).name}")
        
        try:
            # Extract 10 key frames
            frames_dir = Path('temp_frames')
            frames_dir.mkdir(exist_ok=True)
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', 'select=\'not(mod(n,300))\',scale=32:32', # Sample every 360 frames, scale to 32x32
                '-vsync', '0',
                '-f', 'image2',
                str(frames_dir / 'frame_%03d.png')
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            # Read frames and create hash
            frame_hashes = []
            for frame_file in sorted(frames_dir.glob('frame_*.png')):
                frame_hash = self._hash_image(frame_file)
                frame_hashes.append(frame_hash)
                frame_file.unlink() # Clean up
                
            # Combine frame hashes
            combined_hash = hashlib.sha256(
                ''.join(frame_hashes).encode()
            ).hexdigest()[:16]
            
            frames_dir.rmdir()
            
            print(f"✅ Perceptual hash: {combined_hash}")
            
            return {
                'video_path': video_path,
                'perceptual_hash': combined_hash,
                'frame_count': len(frame_hashes),
                'algorithm': 'simple_perceptual'
            }
            
        except Exception as e:
            return {'error': f'Error generating perceptual hash: {str(e)}'}
        
    def _hash_image(self, image_path: Path) -> str:
        """Hash a single image file"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
        
    def compare_hashes(self, hash1: str, hash2: str) -> float:
        """
        Compare two perceptual hashes
        Returns similarity score (0.0-1.0)
        """
        # Simple character comparison
        matches = sum(c1 == c2 for c1, c2 in zip(has1, hash2))
        similarity = matches / len(hash1) if len(hash1) > 0 else 0.0
        
        return similarity