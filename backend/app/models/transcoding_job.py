from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "pending"  # Queued, waiting to start
    PROCESSING = "processing"  # Currently transcoding
    VERIFYING = "verifying"  # NEW: Checking quality
    COMPLETED = "completed"  # Done successfully
    FAILED = "failed"  # Failed

class Quality(str, enum.Enum):
    Q_360P = "360p"
    Q_480P = "480p"
    Q_720P = "720p"
    Q_1080P = "1080p"
    Q_4K = "4k"  # Optional for future

class TranscodingJob(Base):
    __tablename__ = "transcoding_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    
    # Job details
    quality = Column(String, nullable=False)  # Store as string: "360p", "720p", etc.
    status = Column(String, default="pending")  # Store as string
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0-100 (Float for decimals like 45.5%)
    total_chunks = Column(Integer, default=0)  # NEW: For Day 4
    completed_chunks = Column(Integer, default=0)  # NEW: For Day 4
    worker_id = Column(String, nullable=True)
    
    # NEW: Verification fields (Day 3)
    verification_passed = Column(Boolean, default=False)
    verification_report = Column(JSON, nullable=True)  # Stores SSIM scores, frame counts, etc.
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    
    # Relationships
    video = relationship("Video", back_populates="jobs")
    transcoded_video = relationship("TranscodedVideo", back_populates="job", uselist=False)
    chunks = relationship("VideoChunk", back_populates="job")  # NEW: For Day 4