"""
Database models for inspection reports
"""
from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean,
    DateTime, Text, DECIMAL, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class InspectionReport(Base):
    """
    Stores complete video inspection reports
    """
    __tablename__ = 'inspection_reports'
    
    # Primary key
    id = Column(Integer, primarykey=True, autoincrement=True)
    inspection_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    
    # File Info
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    inspected_at = Column(DateTime, default=datetime.utcnow)
    
    # Video Properties
    video_codec = Column(String(50))
    video_width = Column(Integer)
    video_height = Column(Integer)
    video_fps = Column(DECIMAL(10, 2))
    video_bitrate = Column(BigInteger)
    video_duration = Column(DECIMAL(10, 2))
    
    # Audio Properties
    audio_codec = Column(String(50))
    audio_bitrate = Column(Integer)
    audio_sample_rate = Column(Integer)
    has_audio = Column(Boolean, default=False)
    
    # Validation Check Results
    container_format_check = Column(String(20))
    codec_support_check = Column(String(20))
    resolution_check = Column(String(20))
    bitrate_check = Column(String(20))
    frame_rate_check = Column(String(20))
    audio_quality_check = Column(String(20))
    black_frames_check = Column(String(20))
    frozen_frames_check = Column(String(20))
    
    # Frame Analysis
    black_frames_percent = Column(DECIMAL(5, 2))
    frozen_frames_percent = Column(DECIMAL(5, 2))
    
    # Issues (stored as JSON)
    issues = Column(JSONB)
    
    # frame detections (stored as JSON for detailed timestamps)
    black_frame_detections = Column(JSONB)
    frozen_frame_detections = Column(JSONB)
    
    # Final Verdict
    status = Column(String(20), nullable=False) # PASSED, FAILED, WARNING
    can_process = Column(Boolean, default=True)
    verdict_message = Column(Text)
    rejection_reasons = Column(JSONB)
    warnings = Column(JSONB)
    
    def __repr__(self):
        return f"<InpectionReport(id={self.inspection_id}, status={self.status})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
           'inspection_id': str(self.inspection_id),
           'filename': self.filename,
           'file_info': {
               'size': self.file_size,
               'path': self.file_path,
               'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
               'inspected_at': self.inspected_at.isoformat() if self.inspected_at else None
           },
           'video': {
               'codec': self.video_codec,
               'width': self.video_width,
               'height': self.video_height,
               'fps': float(self.video_fps) if self.video_fps else None,
               'bitrate': self.video_bitrate,
               'duration': float(self.video_duration) if self.video_duration else None
           },
           'audio': {
                'codec': self.audio_codec,
                'bitrate': self.audio_bitrate,
                'sample_rate': self.audio_sample_rate,
                'has_audio': self.has_audio
            } if self.has_audio else None,
           'checks': {
                'container_format': self.container_format_check,
                'codec_support': self.codec_support_check,
                'resolution': self.resolution_check,
                'bitrate': self.bitrate_check,
                'frame_rate': self.frame_rate_check,
                'audio_quality': self.audio_quality_check,
                'black_frames': self.black_frames_check,
                'frozen_frames': self.frozen_frames_check
            },
           'frame_analysis': {
                'black_frames': {
                    'percent': float(self.black_frames_percent) if self.black_frames_percent else 0,
                    'detections': self.black_frame_detections or [],
                    'passed': self.black_frames_check == 'PASS'
                },
                'frozen_frames': {
                    'percent': float(self.frozen_frames_percent) if self.frozen_frames_percent else 0,
                    'detections': self.frozen_frame_detections or [],
                    'passed': self.frozen_frames_check == 'PASS'
                }
           },
           'issues': self.issues or [],
           'verdict': {
                'status': self.status,
                'can_process': self.can_process,
                'message': self.verdict_message,
                'rejection_reasons': self.rejection_reasons or [],
                'warnings': self.warnings or []
            }
        }