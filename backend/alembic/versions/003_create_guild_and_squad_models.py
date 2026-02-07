"""Create Guild and Squad models

Revision ID: 003
Revises: 002
Create Date: 2024-01-24 16:00:00.000000

Implements Requirements 2.5, 2.6 (Guild and Squad matching).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create guilds, guild_memberships, squads, and squad_memberships tables.
    """
    # Create guild_type enum
    guild_type_enum = postgresql.ENUM('public', 'premium', 'private', name='guildtype')
    guild_type_enum.create(op.get_bind())
    
    # Create squad_status enum
    squad_status_enum = postgresql.ENUM('forming', 'active', 'completed', name='squadstatus')
    squad_status_enum.create(op.get_bind())
    
    # Create guilds table
    op.create_table(
        'guilds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('interest_area', sa.String(), nullable=False),
        sa.Column('guild_type', guild_type_enum, nullable=False, server_default='public'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('allowed_email_domains', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('custom_objectives', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('expert_facilitator_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('certification_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['expert_facilitator_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guilds_id'), 'guilds', ['id'], unique=False)
    op.create_index(op.f('ix_guilds_interest_area'), 'guilds', ['interest_area'], unique=False)
    
    # Create guild_memberships table
    op.create_table(
        'guild_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guild_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_guild_memberships_id'), 'guild_memberships', ['id'], unique=False)
    op.create_index(op.f('ix_guild_memberships_user_id'), 'guild_memberships', ['user_id'], unique=False)
    op.create_index(op.f('ix_guild_memberships_guild_id'), 'guild_memberships', ['guild_id'], unique=False)
    
    # Create squads table
    op.create_table(
        'squads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guild_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', squad_status_enum, nullable=False, server_default='forming'),
        sa.Column('member_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_syllabus_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('syllabus_start_date', sa.DateTime(), nullable=True),
        sa.Column('current_day', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chat_channel_id', sa.String(), nullable=True),
        sa.Column('average_completion_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('average_skill_level', sa.Float(), nullable=False, server_default='0.0'),
        sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_squads_id'), 'squads', ['id'], unique=False)
    op.create_index(op.f('ix_squads_guild_id'), 'squads', ['guild_id'], unique=False)
    
    # Create squad_memberships table
    op.create_table(
        'squad_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('squad_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['squad_id'], ['squads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_squad_memberships_id'), 'squad_memberships', ['id'], unique=False)
    op.create_index(op.f('ix_squad_memberships_user_id'), 'squad_memberships', ['user_id'], unique=False)
    op.create_index(op.f('ix_squad_memberships_squad_id'), 'squad_memberships', ['squad_id'], unique=False)


def downgrade() -> None:
    """
    Drop guilds, guild_memberships, squads, and squad_memberships tables.
    """
    # Drop tables
    op.drop_index(op.f('ix_squad_memberships_squad_id'), table_name='squad_memberships')
    op.drop_index(op.f('ix_squad_memberships_user_id'), table_name='squad_memberships')
    op.drop_index(op.f('ix_squad_memberships_id'), table_name='squad_memberships')
    op.drop_table('squad_memberships')
    
    op.drop_index(op.f('ix_squads_guild_id'), table_name='squads')
    op.drop_index(op.f('ix_squads_id'), table_name='squads')
    op.drop_table('squads')
    
    op.drop_index(op.f('ix_guild_memberships_guild_id'), table_name='guild_memberships')
    op.drop_index(op.f('ix_guild_memberships_user_id'), table_name='guild_memberships')
    op.drop_index(op.f('ix_guild_memberships_id'), table_name='guild_memberships')
    op.drop_table('guild_memberships')
    
    op.drop_index(op.f('ix_guilds_interest_area'), table_name='guilds')
    op.drop_index(op.f('ix_guilds_id'), table_name='guilds')
    op.drop_table('guilds')
    
    # Drop enums
    squad_status_enum = postgresql.ENUM('forming', 'active', 'completed', name='squadstatus')
    squad_status_enum.drop(op.get_bind())
    
    guild_type_enum = postgresql.ENUM('public', 'premium', 'private', name='guildtype')
    guild_type_enum.drop(op.get_bind())
