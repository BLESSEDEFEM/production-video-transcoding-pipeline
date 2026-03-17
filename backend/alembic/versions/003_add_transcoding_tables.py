"""add transcoding tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # Create transcoding_jobs table
    op.create_table('transcoding_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('quality', sa.String(), nullable=False),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('progress', sa.Float(), default=0.0),
        sa.Column('total_chunks', sa.Integer(), default=0),
        sa.Column('completed_chunks', sa.Integer(), default=0),
        sa.Column('worker_id', sa.String(), nullable=True),
        sa.Column('verification_passed', sa.Boolean(), default=False),
        sa.Column('verification_report', postgresql.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], )
    )
    
    # Create transcoded_videos table
    op.create_table('transcoded_videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_video_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('quality', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('fingerprint_hash', sa.String(), nullable=True),
        sa.Column('fingerprint_data', postgresql.JSON(), nullable=True),
        sa.Column('frame_count_matches', sa.Boolean(), default=False),
        sa.Column('fingerprint_similarity', sa.Float(), nullable=True),
        sa.Column('chunks_verified', sa.Boolean(), default=False),
        sa.Column('boundary_issues', sa.Boolean(), default=False),
        sa.Column('thumbnail_path', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['original_video_id'], ['videos.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['transcoding_jobs.id'], )
    )

def downgrade():
    op.drop_table('transcoded_videos')
    op.drop_table('transcoding_jobs')