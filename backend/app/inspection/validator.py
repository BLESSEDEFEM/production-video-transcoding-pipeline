"""
Video Validation Logic
Validates metadat against defined rules
"""
from typing import Dict, List, Tuple
from .rules import ValidationRules
from .frame_analyzer import FrameAnalyzer

class ValidationResult:
    """Stores validation results"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def add_error(self, message: str):
        """Add error (causes rejections)"""
        self.errors.append(message)
    
    def add_warning(self, message: str):
        """Add warning (doesn't cause rejection)"""
        self.warnings.append(message)
        
    def add_info(self, message: str):
        """Ädd informational message"""
        self.info.append(message)
        
    def is_valid(self) -> bool:
        """Check if validation passed"""
        return len(self.errors) == 0
    
    def get_summary(self) -> Dict:
        """Get validation summary"""
        return {
            'valid': self.is_valid(),
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
        
     
class VideoValidator:
    """
    Validates video metadata against requirements
    """
    
    def __init__(self, rules: ValidationRules = None):
        self.rules = rules or ValidationRules() 
        
    def validate(self, metadata: Dict) -> ValidationResult:
        """
        Validate video metadata
        
        Args:
            metadata: Metadata dictionary from Metadata Extractor
            
        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult()
        
        print(f"\n🔍 Validating video...")
        
        # Check for extraction errors
        if 'error' in metadata:
            result.add_error(f"Metadata extraction failed: {metadata['error']}")
            return result
        
        # Validate video straem exists
        if not metadata.get('video'):
            result.add_error("No video stream found in file")
            return result
            
        video = metadata['video']
        audio = metadata.get('audio')
        file_info = metadata['file']
        
        # Run all validations
        self._validate_container(file_info, result)
        self._validate_video_codec(video, result)
        self._validate_resolution(video, result)
        self._validate_bitrate(video, result)
        self._validate_fps(video, result)
        self._validate_audio(audio, result)
        
        # Print results
        self._print_results(result)
        
        return result
    
    def _validate_container(self, file_info: Dict, result: ValidationResult):
        """Validate container format"""
        format_name = file_info['format_name']
        
        supported = any(
            fmt in format_name
            for fmt in self.rules.SUPPORTED_CONTAINERS
        )
        
        if not supported:
            result.add_error(
                f"Unsupported container format: {format_name}"
            )
            print(f"   ❌ Container: {format_name} (unsupported)")
        else:
            result.add_info(f"Container: {format_name}")
            print(f"   ✅ Container: {format_name}")
            
    def _validate_video_codec(self, video: Dict, result: ValidationResult):
        """Validate video codec"""
        codec = video['codec']
        
        if codec not in self.rules.SUPPORTED_VIDEO_CODECS:
            result.add_error(
                f"Unsupported video codec: {codec} "
                f"(supported: {', '.join(self.rules.SUPPORTED_VIDEO_CODECS)})"
            )
            print(f"   ❌ Video codec: {codec} (unsupported)")
        else:
            result.add_info(f"Video codec: {codec}")
            print(f"   ✅ Video codec: {codec}")
            
    def _validate_resolution(self, video: Dict, result: ValidationResult):
        """Validate video resolution"""
        width = video['width']
        height = video['height']
        
        # Check minimum
        if width < self.rules.MIN_WIDTH or height < self.rules.MIN_HEIGHT:
            result.add_error(
                f"Resolution too low: {width}×{height}"
                f"(minimum: {self.rules.MIN_WIDTH}×{self.rules.MIN_HEIGHT})"
            )
            print(f"   ❌ Resolution: {width}×{height} (too low)")
            return
        
        # Check maximum
        if width > self.rules.MAX_WIDTH or height > self.rules.MAX_HEIGHT:
            result.add_error(
                f"Resolution too high: {width}×{height}"
            f"(maximum: {self.rules.MAX_WIDTH}×{self.rules.MAX_HEIGHT})"
            )
            print(f"   ❌ Resolution: {width}×{height} (too high)")
            return
        
        # Check even dimensions
        if width % 2 != 0 or height % 2 != 0:
            result.add_error(
                f"Dimensions must be even: {width}×{height}"
            )
            print(f"   ❌ Resolution: {width}×{height} (odd dimensions)")
            return
        
        # Check aspect ratio
        aspect_ratio = width / height
        if aspect_ratio < 1.0 or aspect_ratio > 3.0:
            result.add_warning(
                f"Unusual aspect ratio: {aspect_ratio:.2f} ({width}×{height})"
            )
            print(f"   ⚠️ Resolution: {width}×{height} (unusual aspect ratio)")
        else:
            result.add_info(f"Resolution: {width}×{height}")
            print(f"   ✅ Resolution: {width}×{height}")
            
    def _validate_bitrate(self, video: Dict, result: ValidationResult):
        """Validates bitrate"""
        bitrate = video['bitrate']
        width = video['width']
        height = video['height']
        
        min_bitrate = self.rules.get_min_bitrate(width, height)
        res_name = self.rules.get_resolution_name(width, height)
        
        if bitrate < min_bitrate:
            result.add_error(
                f"Bitrate too low: {video['bitrate_mbps']} Mbps "
                f"(minimum {min_bitrate/1_000_000} Mbps for {res_name})"
            )
            print(f"   ❌ Bitrate: {video['bitrate_mbps']} Mbps (too low for {res_name})")
        else:
            result.add_info(f"Bitrate: {video['bitrate_mbps']} Mbps")
            print(f"   ✅ Bitrate: {video['bitrate_mbps']} Mbps")
            
        # Warn if excessively high
        if bitrate > min_bitrate * 10:
            result.add_warning(
                f"Bitrate very high: {video['bitrate_mbps']} Mbps"
                f"(file will be large)"
            )
            
    def _validate_fps(self, video: Dict, result: ValidationResult):
        """Validate frame rate"""
        fps = video['fps']
        
        if fps < self.rules.MIN_FPS:
            result.add_error(
                f"Frame rate too low: {fps} FPS "
                f"(minimum: {self.rules.MIN_FPS} FPS)"
            )
            print(f"   ❌ FPS {fps} (too low)")
        elif fps > self.rules.MAX_FPS:
            result.add_warning(
                f"Frame rate very high: {fps} FPS"
                f"(may cause processing issues)"
            )
            print(f"   ⚠️  FPS: {fps} (very high)")
        else:
            # Check if standard frame rate
            standard_rates = [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]
            is_standard = any(abs(fps - rate) < 0.1 for rate in standard_rates)
            
            if not is_standard:
                result.add_warning(f"Non-standard frame rate: {fps} FPS")
                print(f"   ⚠️  FPS: {fps} (non-standard)")
            else:
                result.add_info(f"FPS: {fps}")
                print(f"   ✅ FPS: {fps}")
                
    def _validate_audio(self, audio: Dict, result: ValidationResult):
        """Validate audio stream"""
        if not audio:
            result.add_warning("No audio track found")
            print(f"   ⚠️  Audio: None")
            return
        
        # Check codec
        codec = audio['codec']
        if codec not in self.rules.SUPPORTED_VIDEO_CODECS:
            result.add_warning(
                f"Unsupported audio codec: {codec} "
                f"(supported: {', '.join(self.rules.SUPPORTED_AUDIO_CODECS)})"
            )
            
        # Check bitrate
        bitrate = audio['bitrate']
        if bitrate < self.rules.MIN_AUDIO_BITRATE:
            result.add_error(
                f"Audio bitrate too low: {audio['bitrate_kbps']} kbps"
                f"(minimum: {self.rules.MIN_AUDIO_BITRATE/1000} kbps)"
            )
            print(f"   ❌ Audio bitrate: {audio['bitrate_kbps']} kbps (too low)")
        else:
            result.add_info(f"Audio: {codec}, {audio['bitrate_kbps']} kbps")
            print(f"    Audio: {codec}, {audio['bitrate_kbps']} kbps")
            
        # Check sample rate
        sample_rate = audio['sample_rate']
        if sample_rate < self.rules.MIN_AUDIO_SAMPLE_RATE:
            result.add_warning(
                f"Audio sample rate too low: {audio['sample_rate_khz']} kHz "
                f"(recommended: {self.rules.MIN_AUDIO_SAMPLE_RATE/1000} kHz+)"
            )
            
    def _print_results(self, result: ValidationResult):
        """Print validation results"""
        print(f"\n{'='*70}")
        print(f"VALIDATION RESULTS")
        print(f"{'='*70}")
        
        if result.is_valid():
            print(f"\n✅ VALIDATION PASSED")
        else:
            print(f"\n❌ VALIDATION FAILED")
            
        print(f"\nSummary:")
        print(f" Errors: {len(result.errors)}")
        print(f" Warnings: {len(result.warnings)}")
        
        if result.errors:
            print(f"\n❌  ERRORS:")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i}. {error}")
                
        if result.warnings:
            print(f"\n⚠️  WARNINGS:")
            for i, warning in enumerate(result.warnings, 1):
                print(f"   {i}. {warning}")
                
        print(f"\n{'='*70}\n")
        
    def validate_with_frames(self, metadata: Dict) -> ValidationResult:
        """
        Complete validation including frame analysis
        """
        # Run basic validation first
        result = self.validate(metadata)
        
        # If basic validation failed, skip frame analysis
        if not result.is_valid():
            return result
        
        # Run frame analysis
        print("\n📊 Running frame-level analysis...")
        
        analyzer = FrameAnalyzer()
        video_path = metadata['file']['path']
        duration = metadata['file']['duration']
        fps = metadata['video']['fps']
        
        frame_analysis = analyzer.analyze_frames(video_path, duration, fps)
        
        # Add results to validation
        black = frame_analysis['black_frames']
        if not black['passed']:
            result.add_error(
                f"Too many black frames: {black['percentage']:.2f}% "
                f"(limit: {analyzer.MAX_BLACK_PERCENT}%)"
            )
        
        frozen = frame_analysis['frozen_frames']
        if not frozen['passed']:
            result.add_error(
                f"Too many frozen frames: {frozen['percentage']:.2f}% "
                f"(limit: {analyzer.MAX_FROZEN_PERCENT}%)"
            )
        
        return result
    
    
# ============================================================================
# Day 3 Adapter Function
# ============================================================================

def validate_video_source(video_path: str) -> Dict:
    """
    Adapter function for Day 3 compatibility
    
    Converts VideoValidator output to expected format
    
    Args:
        video_path: Path to video file
        
    Returns:
        dict with 'passed', 'summary', 'errors', 'warnings', 'metadata'
    """
    # Import here to avoid circular dependency
    from app.inspection.metadata import extract_metadata
    
    # Extract metadata first
    metadata = extract_metadata(video_path)
    
    if 'error' in metadata:
        return {
            'passed': False,
            'summary': 'Metadata extraction failed',
            'errors': [metadata['error']],
            'warnings': [],
            'metadata': {}
        }
    
    # Run validation
    validator = VideoValidator()
    result = validator.validate(metadata)
    
    # Convert to Day 3 format
    return {
        'passed': result.is_valid(),
        'summary': result.get_summary()['valid'] and 'Validation passed' or f"{len(result.errors)} error(s) found",
        'errors': result.errors,
        'warnings': result.warnings,
        'metadata': {
            'resolution': f"{metadata['video']['width']}x{metadata['video']['height']}",
            'duration': metadata['file']['duration'],
            'codec': metadata['video']['codec'],
            'bitrate': metadata['video']['bitrate'] // 1000  # Convert to kbps
        }
    }