from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class VideoStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    INSPECTING = "inspecting"  # Being validated
    REJECTED = "rejected"  # Failed validation (use this instead of INSPECTION_FAILED)
    APPROVED = "approved"  # Passed validation
    QUEUED = "queued"  # Jobs created, waiting in queue
    PROCESSING = "processing"  # Currently transcoding
    COMPLETED = "completed"  # All done
    FAILED = "failed"  # Transcoding failed
    
class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Basic info
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    file_size = Column(Integer)  # bytes
    duration = Column(Float)  # seconds
    
    # Video metadata
    resolution = Column(String)  # "1920x1080"
    codec = Column(String)  # "h264"
    bitrate = Column(Integer)  # kbps (NEW - needed for validation)
    fps = Column(Float)  # frames per second (NEW - needed for validation)
    
    # Status
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.UPLOADED)
    
    # Fingerprinting (Netflix-grade feature)
    fingerprint_hash = Column(String, nullable=True)  # NEW - SHA256 hash
    fingerprint_data = Column(JSON, nullable=True)  # NEW - Full metadata
    
    # Inspection/Quality
    source_quality_score = Column(Float)  # KEEP - Your original idea was good!
    inspection_passed = Column(Boolean, default=False)  # NEW - Quick check flag
    inspection_report = Column(JSON, nullable=True)  # NEW - Inline JSON (simpler than separate table)
    rejection_reason = Column(Text, nullable=True)  # NEW - User-friendly message
    
    # Visual
    thumbnail_path = Column(String, nullable=True)  # NEW - For video preview
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="videos")
    transcoded_versions = relationship("TranscodedVideo", back_populates="original_video")
    jobs = relationship("TranscodingJob", back_populates="video")  # CHANGED: uselist=True (multiple jobs per video)