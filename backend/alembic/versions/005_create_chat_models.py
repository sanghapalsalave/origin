"""Create chat models

Revision ID: 005
Revises: 004
Create Date: 2024-01-24 19:00:00.000000

Implements Requirement 9.1: Real-time squad chat.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chat_channels, messages, attachments, and message_mentions tables."""
    
    # Create message_type enum
    message_type_enum = postgresql.ENUM(
        'text', 'code', 'image', 'file',
        name='messagetype'
    )
    message_type_enum.create(op.get_bind())
    
    # Create chat_channels table
    op.create_table(
        'chat_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('squad_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('realtime_channel_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['squad_id'], ['squads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('squad_id'),
        sa.UniqueConstraint('realtime_channel_id')
    )
    op.create_index(op.f('ix_chat_channels_id'), 'chat_channels', ['id'], unique=False)
    op.create_index(op.f('ix_chat_channels_squad_id'), 'chat_channels', ['squad_id'], unique=False)
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', message_type_enum, nullable=False, server_default='text'),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.Column('realtime_message_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['chat_channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'], unique=False)
    op.create_index(op.f('ix_messages_channel_id'), 'messages', ['channel_id'], unique=False)
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_messages_sent_at'), 'messages', ['sent_at'], unique=False)
    
    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('storage_url', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attachments_id'), 'attachments', ['id'], unique=False)
    op.create_index(op.f('ix_attachments_message_id'), 'attachments', ['message_id'], unique=False)
    
    # Create message_mentions table
    op.create_table(
        'message_mentions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mentioned_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_mentions_id'), 'message_mentions', ['id'], unique=False)
    op.create_index(op.f('ix_message_mentions_message_id'), 'message_mentions', ['message_id'], unique=False)
    op.create_index(op.f('ix_message_mentions_mentioned_user_id'), 'message_mentions', ['mentioned_user_id'], unique=False)


def downgrade() -> None:
    """Drop chat_channels, messages, attachments, and message_mentions tables."""
    
    # Drop tables
    op.drop_index(op.f('ix_message_mentions_mentioned_user_id'), table_name='message_mentions')
    op.drop_index(op.f('ix_message_mentions_message_id'), table_name='message_mentions')
    op.drop_index(op.f('ix_message_mentions_id'), table_name='message_mentions')
    op.drop_table('message_mentions')
    
    op.drop_index(op.f('ix_attachments_message_id'), table_name='attachments')
    op.drop_index(op.f('ix_attachments_id'), table_name='attachments')
    op.drop_table('attachments')
    
    op.drop_index(op.f('ix_messages_sent_at'), table_name='messages')
    op.drop_index(op.f('ix_messages_user_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_channel_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_chat_channels_squad_id'), table_name='chat_channels')
    op.drop_index(op.f('ix_chat_channels_id'), table_name='chat_channels')
    op.drop_table('chat_channels')
    
    # Drop enum
    message_type_enum = postgresql.ENUM(
        'text', 'code', 'image', 'file',
        name='messagetype'
    )
    message_type_enum.drop(op.get_bind())
