"""
Validations Rules Configuration
Centralized validation thresholds and requirements
"""


class ValidationRules:
    """
    Centralized validation rules
    Makes it easy to adjust thresholds
    """
    
    # Resolution limits
    MIN_WIDTH = 640
    MIN_HEIGHT = 360
    MAX_WIDTH = 3840
    MAX_HEIGHT = 2160
    
    # Bitrate limits (in bps)
    MIN_BITRATE_480P = 500_000    # 500 kbps
    MIN_BITRATE_720P = 1_000_000  # 1 Mbps
    MIN_BITRATE_1080P = 2_000_000 # 2 Mbps
    MIN_BITRATE_4K = 10_000_000   # 10 Mbps
    
    # Frame rate limits
    MIN_FPS = 20
    MAX_FPS =  120
    
    # Audio limits
    MIN_AUDIO_BITRATE  = 64_000   # 64 kbps
    MIN_AUDIO_SAMPLE_RATE = 32000 # 32 kHz
    
    # Supported codecs
    SUPPORTED_VIDEO_CODECS = [
        'h264', 'hevc', 'vp9', 'av1', 'mpeg4'
    ]
    
    SUPPORTED_AUDIO_CODECS = [
        'aac', 'mp3', 'opus', 'vorbis'
    ]
    
    SUPPORTED_CONTAINERS = [
        'mov,mp4,m4a,3gp,3g2,mj2',
        'matroska,webm',
        'avi'
    ]
    
    @classmethod
    def get_min_bitrate(cls, width: int, height: int) -> int:
        """Get minimum bitrate based on resolution"""
        pixels = width * height
        
        if pixels >= 1920 * 1080:   # 1080p
            return cls.MIN_BITRATE_1080P
        elif pixels >= 1280 * 720:  # 720p
            return cls.MIN_BITRATE_720P
        elif pixels >= 854 * 480:   # 480p
            return cls.MIN_BITRATE_480P
        else:
            return cls.MIN_BITRATE_480P
        
    @classmethod
    def get_resolution_name(cls, width: int, height: int) -> str:
        """Get common name for resolution"""
        pixels = width * height
        
        if pixels >= 3840 * 2160:
            return "4K"
        elif pixels >= 1920 * 1080:
            return "1080p"
        elif pixels >= 1280 * 720:
            return "720p"
        elif pixels >= 854 * 480:
            return "480p"
        else:
            return "SD"