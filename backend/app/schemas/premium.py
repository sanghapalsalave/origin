"""
Premium and B2B Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# Subscription Schemas

class SubscriptionCreate(BaseModel):
    """Schema for creating a premium subscription."""
    plan_name: str = Field(..., description="Subscription plan name (monthly, annual)")
    price: int = Field(..., description="Price in cents")


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: UUID
    user_id: UUID
    status: str
    start_date: datetime
    end_date: datetime
    plan_name: str
    price: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Certificate Schemas

class CertificateResponse(BaseModel):
    """Schema for certificate response."""
    id: UUID
    user_id: UUID
    guild_id: UUID
    certificate_name: str
    description: str
    verification_code: str
    ai_verified: bool
    issued_at: datetime
    
    class Config:
        from_attributes = True


# Company Schemas

class CompanyCreate(BaseModel):
    """Schema for creating a company."""
    name: str = Field(..., description="Company name")
    description: Optional[str] = Field(None, description="Company description")
    allowed_email_domains: List[str] = Field(..., description="Allowed email domains for employees")


class CompanyResponse(BaseModel):
    """Schema for company response."""
    id: UUID
    name: str
    description: Optional[str]
    allowed_email_domains: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Private Guild Schemas

class PrivateGuildCreate(BaseModel):
    """Schema for creating a private guild."""
    name: str = Field(..., description="Guild name")
    interest_area: str = Field(..., description="Interest area/skill focus")
    custom_objectives: List[str] = Field(..., description="Custom learning objectives")


class PrivateGuildResponse(BaseModel):
    """Schema for private guild response."""
    id: UUID
    name: str
    interest_area: str
    guild_type: str
    company_id: Optional[UUID]
    allowed_email_domains: Optional[List[str]]
    custom_objectives: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Analytics Schemas

class GuildAnalytics(BaseModel):
    """Schema for guild-specific analytics."""
    guild_id: str
    guild_name: str
    interest_area: str
    member_count: int
    completion_rate: float


class CompanyAnalyticsResponse(BaseModel):
    """Schema for company analytics response."""
    company_id: str
    company_name: str
    total_employees: int
    active_employees: int
    guilds: List[GuildAnalytics]
    overall_completion_rate: float


# Employee Access Schemas

class EmployeeAccessRevoke(BaseModel):
    """Schema for revoking employee access."""
    user_id: UUID = Field(..., description="Employee user ID")
    guild_id: Optional[UUID] = Field(None, description="Specific guild ID (if None, revoke all)")
