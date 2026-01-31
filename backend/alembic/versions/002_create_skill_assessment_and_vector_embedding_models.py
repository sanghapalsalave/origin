"""Create SkillAssessment and VectorEmbedding models

Revision ID: 002
Revises: 001
Create Date: 2024-01-24 15:30:00.000000

Implements Requirements 1.3, 1.4, 1.5, 1.6 (portfolio analysis and skill assessment).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create skill_assessments and vector_embeddings tables.
    """
    # Create skill_assessments table
    op.create_table(
        'skill_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.Enum('GITHUB', 'LINKEDIN', 'RESUME', 'PORTFOLIO_WEBSITE', 'MANUAL', 'COMBINED', 
                                    name='assessmentsource'), nullable=False),
        sa.Column('skill_level', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('detected_skills', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('experience_years', sa.Float(), nullable=True),
        sa.Column('proficiency_levels', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('analysis_summary', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skill_assessments_id'), 'skill_assessments', ['id'], unique=False)
    op.create_index(op.f('ix_skill_assessments_user_id'), 'skill_assessments', ['user_id'], unique=False)
    
    # Create vector_embeddings table
    op.create_table(
        'vector_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pinecone_id', sa.String(), nullable=False),
        sa.Column('skill_level', sa.Integer(), nullable=False),
        sa.Column('learning_velocity', sa.Float(), nullable=False),
        sa.Column('timezone_offset', sa.Float(), nullable=False),
        sa.Column('language_code', sa.String(), nullable=False),
        sa.Column('interest_area', sa.String(), nullable=False),
        sa.Column('embedding_version', sa.String(), nullable=False, server_default='v1'),
        sa.Column('dimensions', sa.Integer(), nullable=False, server_default='384'),
        sa.Column('extra_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vector_embeddings_id'), 'vector_embeddings', ['id'], unique=False)
    op.create_index(op.f('ix_vector_embeddings_user_id'), 'vector_embeddings', ['user_id'], unique=True)
    op.create_index(op.f('ix_vector_embeddings_pinecone_id'), 'vector_embeddings', ['pinecone_id'], unique=True)


def downgrade() -> None:
    """
    Drop skill_assessments and vector_embeddings tables.
    """
    op.drop_index(op.f('ix_vector_embeddings_pinecone_id'), table_name='vector_embeddings')
    op.drop_index(op.f('ix_vector_embeddings_user_id'), table_name='vector_embeddings')
    op.drop_index(op.f('ix_vector_embeddings_id'), table_name='vector_embeddings')
    op.drop_table('vector_embeddings')
    
    op.drop_index(op.f('ix_skill_assessments_user_id'), table_name='skill_assessments')
    op.drop_index(op.f('ix_skill_assessments_id'), table_name='skill_assessments')
    op.drop_table('skill_assessments')
    
    # Drop the enum type
    op.execute('DROP TYPE assessmentsource')
