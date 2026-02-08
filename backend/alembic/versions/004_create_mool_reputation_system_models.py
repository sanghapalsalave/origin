"""Create Mool reputation system models

Revision ID: 004
Revises: 003
Create Date: 2024-01-24 18:00:00.000000

Implements Requirements 7.1, 7.2, 8.1 (Mool reputation system and level-up verification).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create work_submissions, peer_reviews, levelup_requests, and project_assessments tables.
    """
    # Create levelup_status enum
    levelup_status_enum = postgresql.ENUM(
        'pending', 'ai_approved', 'peer_review', 'approved', 'rejected',
        name='levelupstatus'
    )
    levelup_status_enum.create(op.get_bind())
    
    # Create work_submissions table
    op.create_table(
        'work_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('squad_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('submission_url', sa.String(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['squad_id'], ['squads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_submissions_id'), 'work_submissions', ['id'], unique=False)
    op.create_index(op.f('ix_work_submissions_user_id'), 'work_submissions', ['user_id'], unique=False)
    op.create_index(op.f('ix_work_submissions_squad_id'), 'work_submissions', ['squad_id'], unique=False)
    
    # Create peer_reviews table
    op.create_table(
        'peer_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('review_content', sa.Text(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('reputation_awarded', sa.Integer(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_id'], ['work_submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_peer_reviews_id'), 'peer_reviews', ['id'], unique=False)
    op.create_index(op.f('ix_peer_reviews_submission_id'), 'peer_reviews', ['submission_id'], unique=False)
    op.create_index(op.f('ix_peer_reviews_reviewer_id'), 'peer_reviews', ['reviewer_id'], unique=False)
    
    # Create levelup_requests table
    op.create_table(
        'levelup_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_level', sa.Integer(), nullable=False),
        sa.Column('target_level', sa.Integer(), nullable=False),
        sa.Column('project_title', sa.String(), nullable=False),
        sa.Column('project_description', sa.Text(), nullable=False),
        sa.Column('project_url', sa.String(), nullable=False),
        sa.Column('status', levelup_status_enum, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_levelup_requests_id'), 'levelup_requests', ['id'], unique=False)
    op.create_index(op.f('ix_levelup_requests_user_id'), 'levelup_requests', ['user_id'], unique=False)
    
    # Create project_assessments table
    op.create_table(
        'project_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('levelup_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_type', sa.String(), nullable=False),
        sa.Column('assessed_by', sa.String(), nullable=False),
        sa.Column('approved', sa.String(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('assessed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['levelup_request_id'], ['levelup_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_assessments_id'), 'project_assessments', ['id'], unique=False)
    op.create_index(op.f('ix_project_assessments_levelup_request_id'), 'project_assessments', ['levelup_request_id'], unique=False)


def downgrade() -> None:
    """
    Drop work_submissions, peer_reviews, levelup_requests, and project_assessments tables.
    """
    # Drop tables
    op.drop_index(op.f('ix_project_assessments_levelup_request_id'), table_name='project_assessments')
    op.drop_index(op.f('ix_project_assessments_id'), table_name='project_assessments')
    op.drop_table('project_assessments')
    
    op.drop_index(op.f('ix_levelup_requests_user_id'), table_name='levelup_requests')
    op.drop_index(op.f('ix_levelup_requests_id'), table_name='levelup_requests')
    op.drop_table('levelup_requests')
    
    op.drop_index(op.f('ix_peer_reviews_reviewer_id'), table_name='peer_reviews')
    op.drop_index(op.f('ix_peer_reviews_submission_id'), table_name='peer_reviews')
    op.drop_index(op.f('ix_peer_reviews_id'), table_name='peer_reviews')
    op.drop_table('peer_reviews')
    
    op.drop_index(op.f('ix_work_submissions_squad_id'), table_name='work_submissions')
    op.drop_index(op.f('ix_work_submissions_user_id'), table_name='work_submissions')
    op.drop_index(op.f('ix_work_submissions_id'), table_name='work_submissions')
    op.drop_table('work_submissions')
    
    # Drop enum
    levelup_status_enum = postgresql.ENUM(
        'pending', 'ai_approved', 'peer_review', 'approved', 'rejected',
        name='levelupstatus'
    )
    levelup_status_enum.drop(op.get_bind())
