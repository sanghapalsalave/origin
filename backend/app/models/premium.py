"""
Premium and B2B data models.

Implements Requirements 10.1-10.5, 11.1-11.5.
"""
from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, ARRAY, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class SubscriptionStatus(str, Enum):
    """Status of premium subscription."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    TRIAL = "trial"


class Subscription(Base):
    """
    Premium subscription model.
    
    Tracks user premium subscriptions for access to premium guilds,
    expert facilitators, and AI-verified certificates.
    
    Implements Requirements 10.1-10.5.
    """
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Subscription details
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Billing
    plan_name = Column(String, nullable=False)  # e.g., "monthly", "annual"
    price = Column(Integer, nullable=False)  # Price in cents
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="subscriptions")
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return (
            self.status == SubscriptionStatus.ACTIVE and
            self.end_date > datetime.utcnow()
        )


class Certificate(Base):
    """
    AI-verified certificate model for premium guild completion.
    
    Certificates are generated when premium guild members complete
    the curriculum and are displayed on user profiles.
    
    Implements Requirements 10.3, 10.4.
    """
    __tablename__ = "certificates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    guild_id = Column(UUID(as_uuid=True), ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Certificate details
    certificate_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Verification
    verification_code = Column(String, nullable=False, unique=True)
    ai_verified = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", backref="certificates")
    guild = relationship("Guild", backref="certificates")
    
    def __repr__(self) -> str:
        return f"<Certificate(id={self.id}, user_id={self.user_id}, guild_id={self.guild_id})>"


class Company(Base):
    """
    Company model for B2B private guilds.
    
    Companies can create private guilds for employee upskilling with
    custom learning objectives and email domain restrictions.
    
    Implements Requirements 11.1-11.5.
    """
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Company details
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Email domain restrictions
    allowed_email_domains = Column(ARRAY(String), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    private_guilds = relationship("Guild", back_populates="company")
    administrators = relationship("CompanyAdministrator", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.name})>"


class CompanyAdministrator(Base):
    """
    Company administrator model.
    
    Administrators can manage private guilds, view analytics, and
    control employee access.
    
    Implements Requirement 11.4.
    """
    __tablename__ = "company_administrators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Permissions
    can_create_guilds = Column(Boolean, default=True, nullable=False)
    can_view_analytics = Column(Boolean, default=True, nullable=False)
    can_manage_employees = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="administrators")
    user = relationship("User", backref="company_admin_roles")
    
    def __repr__(self) -> str:
        return f"<CompanyAdministrator(id={self.id}, company_id={self.company_id}, user_id={self.user_id})>"


class EmployeeAccess(Base):
    """
    Employee access model for tracking company employee guild access.
    
    Tracks which employees have access to which private guilds and
    maintains learning history even after access is revoked.
    
    Implements Requirement 11.5.
    """
    __tablename__ = "employee_access"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    guild_id = Column(UUID(as_uuid=True), ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Access control
    access_granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_revoked_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    company = relationship("Company", backref="employee_accesses")
    user = relationship("User", backref="employee_accesses")
    guild = relationship("Guild", backref="employee_accesses")
    
    def __repr__(self) -> str:
        return f"<EmployeeAccess(id={self.id}, user_id={self.user_id}, guild_id={self.guild_id}, active={self.is_active})>"
