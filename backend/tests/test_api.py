"""
Automated API tests for the video transcoding pipeline.

Run with: pytest tests/test_api.py -v

These tests use FastAPI's TestClient which creates an in-memory
server — no Docker, no real database needed.

We override the database dependency with an in-memory SQLite database
and mock external services (MinIO, Redis) so tests run fast and isolated.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

# ── Setup: import the app and database pieces ──
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.models.transcoding_job import TranscodingJob
from app.models.transcoded_video import TranscodedVideo
from app.models.video_chunk import VideoChunk
from app.utils.auth import hash_password, create_access_token


# ─────────────────────────────────────────────────────────────────
# TEST DATABASE SETUP
# ─────────────────────────────────────────────────────────────────
# Instead of PostgreSQL, we use SQLite in memory.
# This means tests don't need Docker running.
# The database is created fresh for each test and destroyed after.

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def override_get_db():
    """Replace the real database with our test database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI to use our test database instead of the real one
app.dependency_overrides[get_db] = override_get_db


# ─────────────────────────────────────────────────────────────────
# FIXTURES — reusable setup for tests
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup_database():
    """
    Create all tables before each test, drop them after.
    
    autouse=True means this runs automatically for every test
    without needing to explicitly request it.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a test HTTP client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Get a database session for directly inserting test data."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """
    Create a test user and return their info + auth token.
    
    This is used by most tests since almost every endpoint
    requires authentication.
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(
        data={"user_id": user.id, "username": user.username}
    )

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest.fixture
def test_video(db_session, test_user):
    """Create a test video record in the database."""
    video = Video(
        user_id=test_user["user"].id,
        filename="test_video.mp4",
        original_path="originals/1/test_video.mp4",
        file_size=1500000,
        status=VideoStatus.APPROVED,
        resolution="1280x720",
        codec="h264",
        fps=30.0,
        duration=10.0,
        inspection_passed=True
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def test_jobs(db_session, test_video):
    """Create test transcoding jobs for the test video."""
    jobs = []
    for quality in ["360p", "720p"]:
        job = TranscodingJob(
            video_id=test_video.id,
            quality=quality,
            status="completed",
            verification_passed=True,
            processing_time=15.5
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        jobs.append(job)
    return jobs


@pytest.fixture
def test_transcoded(db_session, test_video, test_jobs):
    """Create test transcoded video records."""
    transcoded = []
    for job in test_jobs:
        tv = TranscodedVideo(
            original_video_id=test_video.id,
            job_id=job.id,
            quality=job.quality,
            file_path=f"transcoded/{test_video.id}/{job.quality}.mp4",
            file_size=500000,
            fingerprint_similarity=95.5
        )
        db_session.add(tv)
        db_session.commit()
        db_session.refresh(tv)
        transcoded.append(tv)
    return transcoded


# ─────────────────────────────────────────────────────────────────
# TESTS: HEALTH & ROOT
# ─────────────────────────────────────────────────────────────────

class TestHealthEndpoints:
    """Test basic server endpoints."""

    def test_root(self, client):
        """GET / should return API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Video Transcoding API" in data["message"]

    def test_health(self, client):
        """GET /health should return healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "video-transcoding-backend"

    def test_metrics(self, client):
        """GET /metrics should return Prometheus format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "python_info" in response.text


# ─────────────────────────────────────────────────────────────────
# TESTS: AUTHENTICATION
# ─────────────────────────────────────────────────────────────────

class TestAuthentication:
    """Test user registration and login."""

    def test_register(self, client):
        """POST /api/auth/register should create a new user."""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        # Password should NOT be in the response
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, test_user):
        """Registering with an existing username should fail."""
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "different@example.com",
            "password": "somepass123"
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_user):
        """Registering with an existing email should fail."""
        response = client.post("/api/auth/register", json={
            "username": "differentuser",
            "email": "test@example.com",
            "password": "somepass123"
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, client, test_user):
        """POST /api/auth/login should return a JWT token."""
        response = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Login with wrong password should fail."""
        response = client.post("/api/auth/login", data={
            "username": "testuser",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with a username that doesn't exist should fail."""
        response = client.post("/api/auth/login", data={
            "username": "nobody",
            "password": "somepass"
        })
        assert response.status_code == 401

    def test_get_me(self, client, test_user):
        """GET /api/auth/me should return current user info."""
        response = client.get(
            "/api/auth/me",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_no_token(self, client):
        """GET /api/auth/me without token should fail."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────
# TESTS: VIDEO ENDPOINTS
# ─────────────────────────────────────────────────────────────────

class TestVideoEndpoints:
    """Test video-related API endpoints."""

    def test_upload_no_auth(self, client):
        """Upload without authentication should fail."""
        response = client.post("/api/upload")
        assert response.status_code == 401

    def test_list_videos(self, client, test_user, test_video):
        """GET /api/videos/list should return user's videos."""
        response = client.get(
            "/api/videos/list",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "test_video.mp4"
        assert data[0]["status"] == "approved"

    def test_list_videos_empty(self, client, test_user):
        """User with no videos should get an empty list."""
        response = client.get(
            "/api/videos/list",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_get_inspection(self, client, test_user, test_video):
        """GET /api/videos/{id}/inspection should return inspection data."""
        response = client.get(
            f"/api/videos/{test_video.id}/inspection",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == test_video.id
        assert data["inspection_passed"] == True
        assert data["status"] == "approved"

    def test_get_inspection_not_found(self, client, test_user):
        """Requesting inspection for nonexistent video should 404."""
        response = client.get(
            "/api/videos/9999/inspection",
            headers=test_user["headers"]
        )
        assert response.status_code == 404

    def test_get_summary(self, client, test_user, test_video, test_jobs, test_transcoded):
        """GET /api/videos/{id}/summary should return complete summary."""
        response = client.get(
            f"/api/videos/{test_video.id}/summary",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["original"]["filename"] == "test_video.mp4"
        assert data["summary"]["total_qualities"] == 2
        assert data["summary"]["all_verified"] == True

    def test_cancel_transcoding(self, client, test_user, test_video, db_session):
        """POST /api/videos/{id}/cancel should cancel pending jobs."""
        # Create a pending job
        job = TranscodingJob(
            video_id=test_video.id,
            quality="1080p",
            status="pending"
        )
        db_session.add(job)
        db_session.commit()

        response = client.post(
            f"/api/videos/{test_video.id}/cancel",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Cancelled 1 job(s)"


# ─────────────────────────────────────────────────────────────────
# TESTS: ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────────

class TestAdminEndpoints:
    """Test admin dashboard API endpoints."""

    def test_admin_stats(self, client, test_user, test_video, test_jobs):
        """GET /api/admin/stats should return system statistics."""
        response = client.get(
            "/api/admin/stats",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["users"]["total"] == 1
        assert data["videos"]["total"] == 1
        assert data["jobs"]["total"] == 2
        assert data["jobs"]["completed"] == 2
        assert data["jobs"]["success_rate"] == 100.0

    def test_admin_stats_no_auth(self, client):
        """Admin stats without auth should fail."""
        response = client.get("/api/admin/stats")
        assert response.status_code == 401

    def test_admin_videos(self, client, test_user, test_video):
        """GET /api/admin/videos should list all videos."""
        response = client.get(
            "/api/admin/videos",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["videos"][0]["owner"] == "testuser"

    def test_admin_videos_filter(self, client, test_user, test_video):
        """Filter videos by status should work."""
        response = client.get(
            "/api/admin/videos?status=approved",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1

        # Filter by a status that doesn't match
        response = client.get(
            "/api/admin/videos?status=rejected",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_admin_jobs(self, client, test_user, test_video, test_jobs):
        """GET /api/admin/jobs should list all jobs."""
        response = client.get(
            "/api/admin/jobs",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_admin_jobs_filter_quality(self, client, test_user, test_video, test_jobs):
        """Filter jobs by quality should work."""
        response = client.get(
            "/api/admin/jobs?quality=360p",
            headers=test_user["headers"]
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["jobs"][0]["quality"] == "360p"