"""add missing columns

Revision ID: 002
Revises: 001
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade():
    # Add missing columns to videos table
    op.add_column('videos', sa.Column('file_size', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('duration', sa.Float(), nullable=True))
    op.add_column('videos', sa.Column('resolution', sa.String(), nullable=True))
    op.add_column('videos', sa.Column('codec', sa.String(), nullable=True))
    op.add_column('videos', sa.Column('bitrate', sa.Integer(), nullable=True))
    op.add_column('videos', sa.Column('fps', sa.Float(), nullable=True))
    op.add_column('videos', sa.Column('fingerprint_hash', sa.String(), nullable=True))
    op.add_column('videos', sa.Column('fingerprint_data', postgresql.JSON(), nullable=True))
    op.add_column('videos', sa.Column('source_quality_score', sa.Float(), nullable=True))
    op.add_column('videos', sa.Column('inspection_passed', sa.Boolean(), default=False))
    op.add_column('videos', sa.Column('inspection_report', postgresql.JSON(), nullable=True))
    op.add_column('videos', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column('videos', sa.Column('thumbnail_path', sa.String(), nullable=True))
    op.add_column('videos', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column('videos', sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()))
    
    # Rename old columns
    op.alter_column('videos', 'upload_date', new_column_name='created_at_old')
    op.alter_column('videos', 'fingerprint_id', new_column_name='fingerprint_hash_old')
    op.alter_column('videos', 'signature_path', new_column_name='fingerprint_data_old')
    op.alter_column('videos', 'quality_score', new_column_name='source_quality_score_old')

def downgrade():
    op.drop_column('videos', 'updated_at')
    op.drop_column('videos', 'thumbnail_path')
    op.drop_column('videos', 'rejection_reason')
    op.drop_column('videos', 'inspection_report')
    op.drop_column('videos', 'inspection_passed')
    op.drop_column('videos', 'source_quality_score')
    op.drop_column('videos', 'fingerprint_data')
    op.drop_column('videos', 'fingerprint_hash')
    op.drop_column('videos', 'fps')
    op.drop_column('videos', 'bitrate')
    op.drop_column('videos', 'codec')
    op.drop_column('videos', 'resolution')
    op.drop_column('videos', 'duration')
    op.drop_column('videos', 'file_size')