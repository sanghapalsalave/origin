"""Create premium and B2B models

Revision ID: 007
Revises: 006
Create Date: 2024-01-24 21:00:00.000000

Implements Requirements 10.1-10.5, 11.1-11.5.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create subscriptions, certificates, companies, and related tables."""
    
    # Create subscription_status enum
    subscription_status_enum = postgresql.ENUM(
        'active', 'expired', 'cancelled', 'trial',
        name='subscriptionstatus'
    )
    subscription_status_enum.create(op.get_bind())
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', subscription_status_enum, nullable=False, server_default='active'),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('plan_name', sa.String(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_id'), 'subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    
    # Create certificates table
    op.create_table(
        'certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guild_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('certificate_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False),
        sa.Column('verification_code', sa.String(), nullable=False),
        sa.Column('ai_verified', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('verification_code')
    )
    op.create_index(op.f('ix_certificates_id'), 'certificates', ['id'], unique=False)
    op.create_index(op.f('ix_certificates_user_id'), 'certificates', ['user_id'], unique=False)
    op.create_index(op.f('ix_certificates_guild_id'), 'certificates', ['guild_id'], unique=False)
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('allowed_email_domains', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)
    
    # Create company_administrators table
    op.create_table(
        'company_administrators',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('can_create_guilds', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_view_analytics', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('can_manage_employees', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_administrators_id'), 'company_administrators', ['id'], unique=False)
    op.create_index(op.f('ix_company_administrators_company_id'), 'company_administrators', ['company_id'], unique=False)
    op.create_index(op.f('ix_company_administrators_user_id'), 'company_administrators', ['user_id'], unique=False)
    
    # Create employee_access table
    op.create_table(
        'employee_access',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guild_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_granted_at', sa.DateTime(), nullable=False),
        sa.Column('access_revoked_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guild_id'], ['guilds.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_employee_access_id'), 'employee_access', ['id'], unique=False)
    op.create_index(op.f('ix_employee_access_company_id'), 'employee_access', ['company_id'], unique=False)
    op.create_index(op.f('ix_employee_access_user_id'), 'employee_access', ['user_id'], unique=False)
    op.create_index(op.f('ix_employee_access_guild_id'), 'employee_access', ['guild_id'], unique=False)


def downgrade() -> None:
    """Drop subscriptions, certificates, companies, and related tables."""
    
    # Drop tables
    op.drop_index(op.f('ix_employee_access_guild_id'), table_name='employee_access')
    op.drop_index(op.f('ix_employee_access_user_id'), table_name='employee_access')
    op.drop_index(op.f('ix_employee_access_company_id'), table_name='employee_access')
    op.drop_index(op.f('ix_employee_access_id'), table_name='employee_access')
    op.drop_table('employee_access')
    
    op.drop_index(op.f('ix_company_administrators_user_id'), table_name='company_administrators')
    op.drop_index(op.f('ix_company_administrators_company_id'), table_name='company_administrators')
    op.drop_index(op.f('ix_company_administrators_id'), table_name='company_administrators')
    op.drop_table('company_administrators')
    
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')
    
    op.drop_index(op.f('ix_certificates_guild_id'), table_name='certificates')
    op.drop_index(op.f('ix_certificates_user_id'), table_name='certificates')
    op.drop_index(op.f('ix_certificates_id'), table_name='certificates')
    op.drop_table('certificates')
    
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    
    # Drop enum
    subscription_status_enum = postgresql.ENUM(
        'active', 'expired', 'cancelled', 'trial',
        name='subscriptionstatus'
    )
    subscription_status_enum.drop(op.get_bind())
