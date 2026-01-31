"""Create User and UserProfile models

Revision ID: 001
Revises: 
Create Date: 2024-01-24 14:45:00.000000

Implements Requirements 15.1 (password hashing with bcrypt).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create users and user_profiles tables.
    """
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('reputation_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_level', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('interest_area', sa.String(), nullable=False),
        sa.Column('skill_level', sa.Integer(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=False),
        sa.Column('preferred_language', sa.String(), nullable=False),
        sa.Column('learning_velocity', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vector_embedding_id', sa.String(), nullable=True),
        sa.Column('github_url', sa.String(), nullable=True),
        sa.Column('linkedin_profile', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('portfolio_url', sa.String(), nullable=True),
        sa.Column('resume_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('manual_skills', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_profiles_user_id'), 'user_profiles', ['user_id'], unique=True)


def downgrade() -> None:
    """
    Drop users and user_profiles tables.
    """
    op.drop_index(op.f('ix_user_profiles_user_id'), table_name='user_profiles')
    op.drop_table('user_profiles')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
