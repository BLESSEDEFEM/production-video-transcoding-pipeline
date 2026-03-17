from app.database import engine, Base
from app.models.user import User
from app.models.video import Video
# from app.models.inspection_report import InspectionReport
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.models.video_chunk import VideoChunk

print("Dropping existing tables...")
Base.metadata.drop_all(bind=engine)

print("Creating database tables...")
Base.metadata.create_all(bind=engine)

print("✅ Tables created!")