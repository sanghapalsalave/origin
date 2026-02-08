"""
Guild and GuildMembership data models.

Implements Requirements 2.5, 2.6 (Guild and Squad matching).
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from enum import Enum
from app.db.base import Base


class GuildType(str, Enum):
    """Type of guild."""
    PUBLIC = "public"
    PREMIUM = "premium"
    PRIVATE = "private"


class Guild(Base):
    """
    Guild model for learning communities focused on specific skills or interest areas.
    
    Guilds are managed by AI Guild Masters and contain multiple squads of learners.
    Supports three types: PUBLIC (free), PREMIUM (paid with expert facilitators),
    and PRIVATE (company-specific B2B).
    
    Implements Requirements:
    - 2.5: Squad activation at threshold
    - 2.6: Squad size constraints
    """
    __tablename__ = "guilds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    name = Column(String, nullable=False)
    interest_area = Column(String, nullable=False, index=True)
    guild_type = Column(SQLEnum(GuildType), nullable=False, default=GuildType.PUBLIC)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # For private guilds (B2B)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)  # Reference to company account
    allowed_email_domains = Column(ARRAY(String), nullable=True)  # e.g., ["company.com", "subsidiary.com"]
    custom_objectives = Column(ARRAY(String), nullable=True)  # Company-specified learning objectives
    
    # For premium guilds
    expert_facilitator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    certification_enabled = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    # Note: Using string references to avoid circular imports
    squads = relationship("Squad", back_populates="guild", cascade="all, delete-orphan", lazy="dynamic")
    memberships = relationship("GuildMembership", back_populates="guild", cascade="all, delete-orphan", lazy="dynamic")
    expert_facilitator = relationship("User", foreign_keys=[expert_facilitator_id], lazy="joined")
    company = relationship("Company", back_populates="private_guilds", foreign_keys=[company_id])
    
    def __repr__(self) -> str:
        return f"<Guild(id={self.id}, name={self.name}, type={self.guild_type}, interest_area={self.interest_area})>"


class GuildMembership(Base):
    """
    Guild membership model for tracking user membership in guilds.
    
    Links users to guilds and tracks when they joined.
    """
    __tablename__ = "guild_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    guild_id = Column(UUID(as_uuid=True), ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="guild_memberships")
    guild = relationship("Guild", back_populates="memberships")
    
    def __repr__(self) -> str:
        return f"<GuildMembership(user_id={self.user_id}, guild_id={self.guild_id})>"
