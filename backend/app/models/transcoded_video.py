from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class TranscodedVideo(Base):
    __tablename__ = "transcoded_videos"
    
    id = Column(Integer, primary_key=True, index=True)
    original_video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("transcoding_jobs.id"), nullable=True)  # Link to job
    
    # Output details
    quality = Column(String, nullable=False)  # "360p", "720p", etc.
    file_path = Column(String, nullable=False)  # S3/MinIO path
    file_size = Column(Integer)  # bytes
    duration = Column(Float)  # seconds
    bitrate = Column(Integer)  # kbps
    
    # NEW: Quality metrics (Day 3)
    quality_score = Column(Float, nullable=True)  # SSIM score (0-1)
    fingerprint_hash = Column(String, nullable=True)  # SHA256 of fingerprint
    fingerprint_data = Column(JSON, nullable=True)  # Full fingerprint metadata
    
    # Frame verification
    frame_count_matches = Column(Boolean, default=False)
    fingerprint_similarity = Column(Float, nullable=True)  # 0-100%
    
    # Assembly verification (for chunked transcoding)
    chunks_verified = Column(Boolean, default=False)
    boundary_issues = Column(Boolean, default=False)
    
    # Visual
    thumbnail_path = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    original_video = relationship("Video", back_populates="transcoded_versions")
    job = relationship("TranscodingJob", back_populates="transcoded_video")