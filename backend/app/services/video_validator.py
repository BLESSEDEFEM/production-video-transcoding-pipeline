"""
Complete Video Source Validation Service
Implements all validation checks in one place
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from .report_generator import ReportGenerator

class ValidationLevel(Enum):
    """Validation severity leveld"""
    REJECT = "reject"
    WARN = "warn"
    INFO = "info"
    
@dataclass    
class ValidationCheck:
    """Single validation check result"""
    name: str
    passed: bool
    level: ValidationLevel
    message: str
    details: Optional[Dict] = None
    
    
class VideoValidator:
    """
    Complete video source validation
    Implements all checks
    """
    
    # Configuration
    MIN_RESOLUTION = (640, 360)
    MAX_RESOLUTION = (3840, 2160)
    MIN_FPS = 20
    MAX_FPS = 120
    MIN_AUDIO_BITRATE = 64_000
    MAX_AV_SYNC_DIFF = 1.0
    MAX_BLACK_PERCENT = 50
    WARN_BLACK_PERCENT = 20
    MAX_SINGLE_FREEZE = 10
    
    SUPPORTED_CODECS = ['h264', 'hevc', 'vp9', 'av1', 'mpeg4']
    SUPPORTED_CONTAINERS = ['mov,mp4,m4a', 'matroska,webm', 'avi']
    
    
    def __init__(self):
        self.checks: List[ValidationCheck] = []
        
    def validate(self, video_path: str) -> Tuple[bool, ValidationCheck]:
        """
        Run complete validation pipeline
        
        Returns: (is_valid, list_of_checks)
        """
        self.checks = []
        video_path = Path(video_path)
        
        print(f"\n{'='*70}")
        print(f"VALIDATING: {video_path.name}")
        print(f"{'='*70}\n")
        
        # Phase 1: File Integrity
        print("📋 Phase 1: File Integrity Checks")
        if not self._check_file_exists(video_path):
            return False, self.checks
        if not self._check_file_readable(video_path):
            return False, self.checks
        if not self._check_file_not_corrupted(video_path):
            return False, self.checks
        
        # Phase 2: Get Video Info
        print("\n📋 Phase 2: Extracting Video Information")
        video_info = self._get_video_info(video_path)
        if not video_info:
            self.checks.append(ValidationCheck(
                "video_info",
                False,
                ValidationLevel.REJECT,
                "Could not extract video information"
            ))
            return False, self.checks
        
        # Phase 3: Container & Codec
        print("\n📋  Phase 3: Container & Container Checks")
        self._check_container_format(video_info)
        self._check_video_codec(video_info)
        
        # Phase 4: Video Properties
        print("\n📋  Phase 4: Video Properties Checks")
        self._check_resolution(video_info)
        self._check_bitrate(video_info)
        self._check_frame_rate(video_info)
        
        # Phase 5: Audio Properties
        print("\n📋 Phase 5: Audio Properties Checks")
        self._check_audio(video_info)
            
        # Phase 6: Content Analysis (optional, expensive)
        print("\n📋 Phase 6: Content Analysis")
        print("   (Skipping black/freeze detection for speed)")
        print("   (Enable in production with async processing)")
        
        # Determine if valid
        rejections = [c for c in self.checks if not c.passed and c.level == ValidationLevel.REJECT]
        warnings = [c for c in self.checks if not c.passed and c.level == ValidationLevel.WARN]
        
        is_valid = len(rejections) == 0
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*70}")
        print(f"Total Result: {len(self.checks)}")
        print(f"Passed: {sum(1 for c in self.checks if c.passed)}")
        print(f"Rejections: {len(rejections)}")
        print(f"Warnings: {len(warnings)}")
        print(f"\nResults: {'✅ VALID' if is_valid else '❌ INVALID'}")
        print(f"{'='*70}\n")
        
        if rejections:
            print(f"❌  REJECTION REASONS:")
            for check in rejections:
                print(f"   • {check.message}")
            print()
            
        if warnings:
            print(f" WARNINGS:")
            for check in warnings:
                print(f"   • {check.message}")
            print()
            
        # Generate complete report
        report_generator = ReportGenerator()
        report = report_generator.generate_report(
            filename=str(video_path.name),
            file_path=str(video_path),
            file_size=video_path.stat().st_size if video_path.exists() else 0,
            video_info=video_info.get('video', {}) if video_info else {},
            audio_info=video_info.get('audio') if video_info else None,
            issues=[{
                'severity': 'reject' if not c.passed and c.level == ValidationLevel.REJECT else 'warn' if not c.passed else 'info',
                'category': c.name.split('_')[0] if '_' in c.name else c.name,
                'message': c.message,
                'details': {}
            } for c in self.checks],
            frame_analysis=None  # We skipped frame analysis
        )

        # Return both the old format AND the new report
        return is_valid, self.checks

    # Phase 1: File Integrity Checks

    def _check_file_exists(self, video_path: Path) -> bool:
        """Checks if file exists"""
        exists = video_path.exists()
        
        check = ValidationCheck(
            "File_exists",
            exists,
            ValidationLevel.REJECT,
            "File exists" if exists else "File not found"
        )
        self.checks.append(check)
        print(f"   {'✅' if exists else '❌'} File exists: {exists}")
        
        return exists

    def _check_file_readable(self, video_path: Path) -> bool:
        """Checks if file is readable"""
        readable = video_path.stat().st_size > 0
        
        check = ValidationCheck(
            "file_readable",
            readable,
            ValidationLevel.REJECT,
            "File has content" if readable else "File is empty (0 bytes)"
        )
        self.checks.append(check)
        print(f"   {'✅' if readable else '❌'} File readable: {readable}")
        
        return readable

    def _check_file_not_corrupted(self, video_path: Path) -> bool:
        """Checks if file is corrupted"""
        try:
            cmd = [
                'ffmpeg',
                '-v', 'error',
                '-i', str(video_path),
                'f', 'null',
                '-'
            ]
            
            print(f"   DEBUG: Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check for corruption indicators
            corruption_keywords = [
                'moov atom not found',
                'invalid data',
                'could not find codec'
            ]
            
            for keyword in corruption_keywords:
                if keyword in result.stderr.lower():
                    check = ValidationCheck(
                        "file_integrity",
                        False,
                        ValidationLevel.REJECT,
                        f"File corrupted: {keyword}",
                        {"error": result.stderr[:200]}
                    )
                    self.checks.append(check)
                    print(f"   ❌ File corrupted: {keyword}")
                    return False
                
            check = ValidationCheck(
                "file_integrity",
                True,
                ValidationLevel.INFO,
                "File integrity OK"
            )
            self.checks.append(check)
            print(f"   ✅ File integrity: OK")
            return True
        
        except Exception as e:
            check = ValidationCheck(
                "file_integrity",
                False,
                ValidationLevel.REJECT,
                f"Error checking file: {str(e)}"
            )
            self.checks.append(check)
            print(f"   ❌ Error: {str(e)}")
            return False
        
    # Phase 2: Get Video Info
        
    def _get_video_info(self, video_path: Path) -> Optional[Dict]:
        """Extract video information using ffprobe"""
        try:    
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            # Extract streams
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream['codec_type'] == 'video' and not video_stream:
                    video_stream = stream
                elif stream['codec_type'] == 'audio' and not audio_stream:
                    audio_stream = stream
                    
            print(f"   ✅ Extracted video information")
            
            return {
                'format': data.get('format', {}),
                'video': video_stream or {},
                'audio': audio_stream
            }
            
        except Exception as e:
            print(f"   ❌ Error extracting info: {e}")
            return None
        
    # Phase 3: Container & Codec Checks
    
    def _check_container_format(self, video_info: Dict):
        """Validate container format"""
        format_name = video_info['format'].get('format_name', '')
        
        supported = any(s in format_name for s in self.SUPPORTED_CONTAINERS)
        
        check = ValidationCheck(
            "container_format",
            supported,
            ValidationLevel.REJECT if not supported else ValidationLevel.INFO,
            f"Container format: {format_name}" if supported else f"Unsupported container: {format_name}",
            {"format": format_name}
        )
        self.checks.append(check)
        print(f"   {'✅' if supported else '❌'} Container: {format_name}")
        
    def _check_video_codec(self, video_info: Dict):
        """Validate video codec"""
        codec = video_info['video'].get('codec_name', '').lower()
        
        supported = codec in self.SUPPORTED_CODECS
        
        check = ValidationCheck(
            "video_codec",
            supported,
            ValidationLevel.REJECT if not supported else ValidationLevel.INFO,
            f"Video codec: {codec}" if supported else f"Unsupported code: {codec}",
            {"codec": codec}
        )
        self.checks.append(check)
        print(f"   {'✅' if supported else '❌'} Video codec: {codec}")
        
    # Phase 4: Video Properties Checks
    
    def _check_resolution(self, video_info: Dict):
        """Validate resolution"""
        width = video_info['video'].get('width', 0)
        height = video_info['video'].get('height', 0)
        
        print(f"   Resolution: {width}×{height}")
        
        # Check minimum
        if width < self.MIN_RESOLUTION[0] or height < self.MIN_RESOLUTION[1]:
            check = ValidationCheck(
                "resolution_minimum",
                False,
                ValidationLevel.REJECT,
                f"Resolution too low: {width}×{height} (minimum {self.MIN_RESOLUTION[0]}×{self.MIN_RESOLUTION[1]})",
                {"width": width, "height": height}
            )
            self.checks.append(check)
            print(f"   ❌ Too low")
            return
        
        # Check maximum
        if width > self.MAX_RESOLUTION[0] or height > self.MAX_RESOLUTION[1]:
            check = ValidationCheck(
                "resolution_maximum",
                False,
                ValidationLevel.REJECT,
                f"Resolution too high: {width}×{height} (maximum {self.MAX_RESOLUTION[0]}×{self.MAX_RESOLUTION[1]})",
                {"width": width, "height": height}
            )
            self.checks.append(check)
            print(f"   ❌ Too high")
            return
        
        # Check even dimensions
        if width % 2 != 0 or height % 2 != 0:
            check = ValidationCheck(
                "resolution_even",
                False,
                ValidationLevel.REJECT,
                f"Dimensions must be even: {width}×{height}",
                {"width": width, "height": height}
            )
            self.checks.append(check)
            print(f"   ❌ Odd dimensions")
            return
        
        # All good
        check = ValidationCheck(
            "resolution",
            True,
            ValidationLevel.INFO,
            f"Resolution OK: {width}×{height}"
        )
        self.checks.append(check)
        print(f"   ✅ Resolution OK")
        
    def _check_bitrate(self, video_info: Dict):
        """Validate bitrate"""
        bitrate = int(video_info['video'].get('bit_rate', 0))
        width = video_info['video'].get('width', 0)
        height = video_info['video'].get('height', 0)
        
        bitrate_mps = bitrate / 1_000_000
        print(f"   Bitrate: {bitrate_mps:.2f} Mbps")
        
        # Determine minimum
        resolution_pixels = width * height
        if resolution_pixels >= 1920 * 1080:
            min_bitrate = 2_000_000
        elif resolution_pixels >= 1280 * 720:
            min_bitrate = 1_000_000
        else:
            min_bitrate = 500_000
            
        if bitrate < min_bitrate:
            check = ValidationCheck(
                "bitrate",
                False,
                ValidationLevel.REJECT,
                f"Bitrate too low: {bitrate_mps:.2f} Mbps (minimum {min_bitrate/1_000_000} Mbps)",
                {"bitrate": bitrate, "minimum": min_bitrate}
            )
            self.checks.append(check)
            print(f"   ❌ Bitrate too low")
        else:
            check = ValidationCheck(
                "bitrate",
                True,
                ValidationLevel.INFO,
                f"Bitrate OK: {bitrate_mps:.2f} Mbps"
            )
            self.checks.append(check)
            print(f"   ✅ Bitrate OK")
        
    def _check_frame_rate(self, video_info: Dict):
        """Validate frame rate"""
        r_frame_rate = video_info['video'].get('r_frame_rate', '0/1')
        
        try:
            num, den = map(int, r_frame_rate.split('/'))
            fps = num / den if den != 0 else 0
        except:
            check = ValidationCheck(
                "frame_rate",
                False,
                ValidationLevel.WARN,
                "Could not parse frame rate"
            )
            self.checks.append(check)
            print(f"   ⚠️ Could not parse FPS")
            return
        
        print(f"   Frame rate: {fps:.2f} FPS")
        
        if fps < self.MIN_FPS:
            check = ValidationCheck(
                "frame_rate",
                False,
                ValidationLevel.REJECT,
                f"Frame rate too low: {fps:.2f} FPS (minimum {self.MIN_FPS} FPS)",
                {"fps": fps}
            )
            self.checks.append(check)
            print(f"   ❌ FPS too low")
        else:
            check = ValidationCheck(
                "frame_rate",
                True,
                ValidationLevel.INFO,
                f"frame rate OK: {fps:.2f} FPS"
            )
            self.checks.append(check)
            print(f"   ✅ Frame rate OK")
            
    # Phase 5: Audio Checks
    
    def _check_audio(self, video_info: Dict):
        """Validate audio properties"""
        audio_info = video_info.get('audio')
        
        if not audio_info:
            check = ValidationCheck(
                "audio",
                True,
                ValidationLevel.WARN,
                "No audio track detected"
            )
            self.checks.append(check)
            print(f"   ⚠️ No audio track")
            return
        
        # Check audio bitrate
        audio_bitrate = int(audio_info.get('bit_rate', 0))
        
        print(f"   Audio bitrate: {audio_bitrate/1000:.0f} kbps")
        
        if audio_bitrate and audio_bitrate < self.MIN_AUDIO_BITRATE:
            check = ValidationCheck(
                "audio_bitrate",
                False,
                ValidationLevel.REJECT,
                f"Audio bitrate too low: {audio_bitrate/1000:.0f} kbps (minimum {self.MIN_AUDIO_BITRATE/1000:.0f} kbps)",
                {"bitrate": audio_bitrate}
            )
            self.checks.append(check)
            print(f"   ❌ Audio bitrate too low")
        else:
            check = ValidationCheck(
                "audio",
                True,
                ValidationLevel.INFO,
                "Audio OK"
            )
            self.checks.append(check)
            print(f"   ✅ Audio OK")