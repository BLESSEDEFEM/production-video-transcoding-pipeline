"""
Video Metadata Extraction
Extracts complete video information using FFprobe
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional

def extract_metadata(video_path: str) -> Dict:
    """Wrapper for MetadataExtractor"""
    extractor = MetadataExtractor()
    return extractor.extract(video_path)

class MetadataExtractor:
    """
    Extract video metadata using FFprobe
    """
    
    def __init__(self, ffprobe_path: str = 'ffprobe'):
        self.ffprobe = ffprobe_path
        
    def extract(self, video_path: str) -> Dict:
        """
        Extract complete metadata from video
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary with metadata or error
        """
        video_path = Path(video_path)
         
        if not video_path.exists():
             return {'error': 'File not found'}
         
        print(f"📊 Extracting metadata: {video_path.name}")
        
        try:
            # Run ffprobe
            cmd = [
                self.ffprobe,
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
                check=True,
                timeout=30
            )
            
            # Parse JSON
            data = json.loads(result.stdout)
            
            # Extract and structure metadata
            metadata = self._structure_metadata(data, video_path)
            
            print(f"✅ Metadata extracted")
            
            return metadata
        
        except subprocess.CalledProcessError as e:
            return {'error': f'FFprobe failed: {e.stderr}'}
        except subprocess.TimeoutExpired:
            return {'error': 'FFprobe timed out (file too large or corrupted?)'}
        except json.JSONDecodeError as e:
            return {'error': f'Invalid JSON from FFprobe: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error {str(e)}'}
        
    def _structure_metadata(self, data: Dict, video_path: Path) -> Dict:
        """Structure raw FFprobe data into organized format"""
        
        # Find streams
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            
            if codec_type == 'video' and not video_stream:
                video_stream = stream
            elif codec_type == 'audio' and not audio_stream:
                audio_stream = stream
                
        format_info = data.get('format', {})
        
        # Build structured metadata
        metadata = {
            'file': {
                'name': video_path.name,
                'path': str(video_path),
                'size': int(format_info.get('size', 0)),
                'size_mb': round(int(format_info.get('size', 0)) / (1024 * 1024), 2),
                'format_name': format_info.get('format_name', 'unknown'),
                'format_long': format_info.get('format_long_name', 'unknown'),
                'duration': float(format_info.get('duration', 0)),
                'bitrate': int(format_info.get('bit_rate', 0))
            },
            'video': self._extract_video_info(video_stream) if video_stream else None,
            'audio': self._extract_audio_info(audio_stream) if audio_stream else None
        }
        
        return metadata
    
    def _extract_video_info(self, stream: Dict) -> Dict:
        """Ëxtract video stream information"""
        
        # Parse frame rate
        r_frame_rate = stream.get('r_frame_rate', '0/1')
        try:
            num, den = map(int, r_frame_rate.split('/'))
            fps = round(num / den, 2) if den != 0 else 0.0
        except:
            fps = 0.0
            
        return {
            'index': stream.get('index'),
            'codec': stream.get('codec_name'),
            'codec_long': stream.get('codec_long_name'),
            'profile': stream.get('profile'),
            'level': stream.get('level'),
            'width': stream.get('width'),
            'height': stream.get('height'),
            'aspect_ratio': f"{stream.get('width')}:{stream.get('height')}",
            'fps': fps,
            'r_frame_rate': r_frame_rate,
            'bitrate': int(stream.get('bit_rate', 0)),
            'bitrate_mbps': round(int(stream.get('bit_rate', 0)) / 1_000_000, 2),
            'pixel_format': stream.get('pix_fmt'),
            'color_space': stream.get('color_space'),
            'duration': float(stream.get('duration', 0)),
            'nb_frames': stream.get('nb_frames')
        }
        
    def _extract_audio_info(self, stream: Dict) -> Dict:
        """Ëxtract audio stream information"""
        
        return {
            'index': stream.get('index'),
            'codec': stream.get('codec_name'),
            'codec_long': stream.get('codec_long_name'),
            'sample_rate': int(stream.get('sample_rate', 0)),
            'sample_rate_khz': round(int(stream.get('sample_rate', 0)) / 1000, 1),
            'channels': stream.get('channels'),
            'channel_layout': stream.get('channel_layout'),
            'bitrate': int(stream.get('bit_rate', 0)),
            'bitrate_kbps': round(int(stream.get('bit_rate', 0)) / 1000, 0),
            'duration': float(stream.get('duration', 0))
        }
        
    def print_metadata(self, metadata: Dict):
        """Pretty print metadata"""
        
        if 'error' in metadata:
            print(f"\n❌ Error: {metadata['error']}")
            return
        
        print(f"\n{'='*70}")
        print(f"VIDEO METADATA")
        print(f"{'='*70}")
        
        # File info
        file_info = metadata['file']
        print(f"\n📁 FILE INFO:")
        print(f"   Name: {file_info['name']}")
        print(f"   Size: {file_info['size_mb']} MB")
        print(f"   Format: {file_info['format_name']}")
        print(f"   Duration: {file_info['duration']:.2f}s")
        
        # Video info
        if metadata['video']:
            video = metadata['video']
            print(f"\n🎬 VIDEO:")
            print(f"   Codec: {video['codec']} ({video['codec_long']})")
            print(f"   Resolution: {video['width']}×{video['height']}")
            print(f"   FPS: {video['fps']}")
            print(f"   Bitrate: {video['bitrate_mbps']} Mbps")
            print(f"   Pixel Format: {video['pixel_format']}")
        else:
            print(f"\n🎬 VIDEO: None")
            
        # Audio info
        if metadata['audio']:
            audio = metadata['audio']
            print(f"\n🔊 AUDIO:")
            print(f"   Codec: {audio['codec']} ({audio['codec_long']})")
            print(f"   Sample Rate: {audio['sample_rate_khz']} kHz")
            print(f"   Channels: {audio['channels']}")
            print(f"   Bitrate: {audio['bitrate_kbps']} kbps")
        else:
            print(f"\n🔊 AUDIO: None")
            
        print(f"\n{'='*70}\n")