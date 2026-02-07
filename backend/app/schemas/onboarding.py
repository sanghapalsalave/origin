"""
Pydantic schemas for onboarding flow.

Implements Requirements:
- 1.1: Interest selection interface
- 1.2: Multiple portfolio input options
- 1.7: Manual entry option
"""
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator
from uuid import UUID


class PortfolioMethod(str, Enum):
    """Portfolio input methods."""
    GITHUB = "github"
    LINKEDIN = "linkedin"
    RESUME = "resume"
    PORTFOLIO_URL = "portfolio_url"
    MANUAL = "manual"


class InterestSelection(BaseModel):
    """
    Schema for interest selection during onboarding.
    
    Implements Requirement 1.1: Interest selection interface
    """
    interest_area: str = Field(
        ...,
        description="Primary interest area for guild matching",
        min_length=2,
        max_length=100,
        examples=["Web Development", "Machine Learning", "Mobile Development"]
    )
    
    @field_validator("interest_area")
    @classmethod
    def validate_interest_area(cls, v: str) -> str:
        """Validate and normalize interest area."""
        v = v.strip()
        if not v:
            raise ValueError("Interest area cannot be empty")
        return v


class PortfolioInput(BaseModel):
    """
    Schema for portfolio input during onboarding.
    
    Implements Requirements:
    - 1.2: Multiple portfolio input options
    - 1.3: GitHub integration
    - 1.4: LinkedIn integration
    - 1.5: Resume upload
    - 1.6: Portfolio URL
    - 1.7: Manual entry
    """
    method: PortfolioMethod = Field(
        ...,
        description="Portfolio input method"
    )
    
    # GitHub
    github_url: Optional[str] = Field(
        None,
        description="GitHub profile URL",
        examples=["https://github.com/username"]
    )
    
    # LinkedIn
    linkedin_data: Optional[Dict[str, Any]] = Field(
        None,
        description="LinkedIn profile data (from OAuth flow)"
    )
    
    # Resume
    resume_file_id: Optional[str] = Field(
        None,
        description="ID of uploaded resume file"
    )
    resume_text: Optional[str] = Field(
        None,
        description="Resume text content (if parsed client-side)"
    )
    
    # Portfolio URL
    portfolio_url: Optional[HttpUrl] = Field(
        None,
        description="Portfolio website URL",
        examples=["https://myportfolio.com"]
    )
    
    # Manual entry
    manual_skills: Optional[List[str]] = Field(
        None,
        description="Manually entered skills",
        examples=[["Python", "JavaScript", "React"]]
    )
    manual_experience_years: Optional[float] = Field(
        None,
        ge=0,
        le=50,
        description="Years of experience"
    )
    manual_proficiency_level: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="Self-assessed proficiency level (1-10)"
    )
    
    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate GitHub URL format."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        # Basic validation - detailed validation in service layer
        if "github.com" not in v.lower() and "/" not in v:
            # Assume it's just a username
            return v
        return v
    
    @field_validator("manual_skills")
    @classmethod
    def validate_manual_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate manual skills list."""
        if v is None:
            return v
        # Remove empty strings and duplicates
        skills = [s.strip() for s in v if s and s.strip()]
        return list(set(skills)) if skills else None
    
    def model_post_init(self, __context: Any) -> None:
        """Validate that appropriate fields are provided for the selected method."""
        if self.method == PortfolioMethod.GITHUB and not self.github_url:
            raise ValueError("github_url is required when method is 'github'")
        elif self.method == PortfolioMethod.LINKEDIN and not self.linkedin_data:
            raise ValueError("linkedin_data is required when method is 'linkedin'")
        elif self.method == PortfolioMethod.RESUME and not (self.resume_file_id or self.resume_text):
            raise ValueError("resume_file_id or resume_text is required when method is 'resume'")
        elif self.method == PortfolioMethod.PORTFOLIO_URL and not self.portfolio_url:
            raise ValueError("portfolio_url is required when method is 'portfolio_url'")
        elif self.method == PortfolioMethod.MANUAL and not self.manual_skills:
            raise ValueError("manual_skills is required when method is 'manual'")


class OnboardingComplete(BaseModel):
    """
    Schema for completing onboarding and creating user profile.
    
    Implements Requirements:
    - 1.9: Create user account with vector embedding
    - 1.11: Collect timezone and preferred language
    """
    display_name: str = Field(
        ...,
        description="User's display name",
        min_length=2,
        max_length=50
    )
    timezone: str = Field(
        ...,
        description="IANA timezone (e.g., 'America/New_York')",
        examples=["America/New_York", "Europe/London", "Asia/Tokyo"]
    )
    preferred_language: str = Field(
        ...,
        description="ISO 639-1 language code (e.g., 'en', 'es', 'fr')",
        min_length=2,
        max_length=2,
        examples=["en", "es", "fr", "de", "ja"]
    )
    confirmed_skill_level: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="User-confirmed skill level (1-10). If not provided, uses analyzed level."
    )
    
    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        """Validate display name."""
        v = v.strip()
        if not v:
            raise ValueError("Display name cannot be empty")
        return v
    
    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone format."""
        v = v.strip()
        if not v:
            raise ValueError("Timezone cannot be empty")
        # Basic validation - detailed validation in service layer
        if "/" not in v and v not in ["UTC", "GMT"]:
            raise ValueError("Invalid timezone format. Use IANA timezone (e.g., 'America/New_York')")
        return v
    
    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        v = v.strip().lower()
        if len(v) != 2:
            raise ValueError("Language code must be 2 characters (ISO 639-1)")
        return v


class OnboardingStatus(BaseModel):
    """
    Response schema for onboarding status.
    """
    user_id: UUID
    interest_area: Optional[str] = None
    portfolio_methods_used: List[PortfolioMethod] = Field(default_factory=list)
    skill_assessments_count: int = 0
    combined_skill_level: Optional[int] = None
    profile_created: bool = False
    vector_embedding_created: bool = False
    onboarding_complete: bool = False
    
    class Config:
        from_attributes = True


class PortfolioAnalysisResult(BaseModel):
    """
    Response schema for portfolio analysis results.
    """
    assessment_id: UUID
    method: PortfolioMethod
    skill_level: int = Field(ge=1, le=10)
    confidence_score: float = Field(ge=0.0, le=1.0)
    detected_skills: List[str]
    experience_years: Optional[float] = None
    analysis_summary: str
    
    class Config:
        from_attributes = True
