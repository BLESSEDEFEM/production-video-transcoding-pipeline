"""
Import all models here so SQLAlchemy can resolve relationships.

When SQLAlchemy sees a relationship like:
    chunks = relationship("VideoChunk", ...)

It needs the VideoChunk class to already be imported somewhere.
This file ensures all models are loaded when the app starts.
"""
from app.models.user import User
from app.models.video import Video
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.models.video_chunk import VideoChunk