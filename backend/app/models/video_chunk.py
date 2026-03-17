from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class VideoChunk(Base):
    __tablename__ = "video_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Which transcoding job does this chunk belong to?
    job_id = Column(Integer, ForeignKey("transcoding_jobs.id"), nullable=False)
    
    # Which piece number? 0, 1, 2, 3...
    chunk_index = Column(Integer, nullable=False)
    
    # Where does this chunk start and end in the original video (in seconds)?
    # Example: chunk_index=1 starts at 30.0 and ends at 60.0
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    
    # Where is the chunk file stored?
    chunk_path = Column(String, nullable=True)         # original cut chunk
    transcoded_path = Column(String, nullable=True)    # transcoded chunk
    
    # Verification
    expected_frames = Column(Integer, nullable=True)   # how many frames SHOULD be there
    actual_frames = Column(Integer, nullable=True)     # how many frames ARE there
    frames_match = Column(Boolean, default=False)
    
    # Did this chunk's join point with the next chunk look clean?
    boundary_ok = Column(Boolean, default=False)
    
    # Overall: did this chunk pass all checks?
    verified = Column(Boolean, default=False)
    
    # Status: pending -> processing -> done / failed
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Link back to the job
    job = relationship("TranscodingJob", back_populates="chunks")
    