"""
Matching API endpoints for squad formation and guild joining.

Implements POST /guilds/{guild_id}/join, GET /squads/matches
with request validation and error handling.

Requirements: 2.2, 2.7
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.base import get_db
from app.services.matching_service import MatchingService
from app.models.user import User
from app.models.squad import Squad
from app.api.dependencies import get_current_user


router = APIRouter()


# Pydantic models for request/response validation

class SquadMatchResponse(BaseModel):
    """Response model for squad match information."""
    squad_id: str = Field(..., description="Squad UUID")
    squad_name: str = Field(..., description="Squad name")
    member_count: int = Field(..., description="Current number of members")
    average_similarity: float = Field(..., description="Average similarity with squad members (0-1)")
    status: str = Field(..., description="Squad status (forming, active, completed)")
    available_slots: int = Field(..., description="Number of available slots")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "squad_id": "123e4567-e89b-12d3-a456-426614174000",
                    "squad_name": "Python Guild Squad 1",
                    "member_count": 13,
                    "average_similarity": 0.85,
                    "status": "active",
                    "available_slots": 2
                }
            ]
        }
    }


class SquadMatchesResponse(BaseModel):
    """Response model for squad matches endpoint."""
    guild_id: str = Field(..., description="Guild UUID")
    guild_name: str = Field(..., description="Guild name")
    matches: List[SquadMatchResponse] = Field(..., description="List of compatible squads")
    in_waiting_pool: bool = Field(..., description="Whether user is in waiting pool")
    waiting_pool_size: int = Field(..., description="Number of users in waiting pool")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "guild_id": "123e4567-e89b-12d3-a456-426614174000",
                    "guild_name": "Python Development Guild",
                    "matches": [
                        {
                            "squad_id": "456e7890-e89b-12d3-a456-426614174000",
                            "squad_name": "Python Guild Squad 1",
                            "member_count": 13,
                            "average_similarity": 0.85,
                            "status": "active",
                            "available_slots": 2
                        }
                    ],
                    "in_waiting_pool": False,
                    "waiting_pool_size": 8
                }
            ]
        }
    }


class JoinGuildResponse(BaseModel):
    """Response model for guild join endpoint."""
    success: bool = Field(..., description="Whether join was successful")
    message: str = Field(..., description="Status message")
    squad_assigned: bool = Field(..., description="Whether user was assigned to a squad")
    squad_id: Optional[str] = Field(None, description="Squad UUID if assigned")
    squad_name: Optional[str] = Field(None, description="Squad name if assigned")
    in_waiting_pool: bool = Field(..., description="Whether user is in waiting pool")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Successfully joined guild and assigned to squad",
                    "squad_assigned": True,
                    "squad_id": "456e7890-e89b-12d3-a456-426614174000",
                    "squad_name": "Python Guild Squad 1",
                    "in_waiting_pool": False
                }
            ]
        }
    }


class WaitingPoolUser(BaseModel):
    """Model for user in waiting pool."""
    user_id: str = Field(..., description="User UUID")
    display_name: str = Field(..., description="User display name")
    skill_level: int = Field(..., description="User skill level (1-10)")
    interest_area: str = Field(..., description="User interest area")
    timezone: str = Field(..., description="User timezone")
    language: str = Field(..., description="User preferred language")
    joined_guild_at: Optional[str] = Field(None, description="When user joined guild (ISO format)")


class WaitingPoolResponse(BaseModel):
    """Response model for waiting pool status."""
    guild_id: str = Field(..., description="Guild UUID")
    guild_name: str = Field(..., description="Guild name")
    waiting_pool_size: int = Field(..., description="Number of users in waiting pool")
    users: List[WaitingPoolUser] = Field(..., description="Users in waiting pool")
    compatible_groups_available: int = Field(..., description="Number of compatible groups that can form squads")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "guild_id": "123e4567-e89b-12d3-a456-426614174000",
                    "guild_name": "Python Development Guild",
                    "waiting_pool_size": 15,
                    "users": [
                        {
                            "user_id": "789e0123-e89b-12d3-a456-426614174000",
                            "display_name": "John Doe",
                            "skill_level": 5,
                            "interest_area": "Python Development",
                            "timezone": "America/New_York",
                            "language": "en",
                            "joined_guild_at": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "compatible_groups_available": 1
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    detail: str = Field(..., description="Error message")


# Dependency to get matching service
def get_matching_service(db: Session = Depends(get_db)) -> MatchingService:
    """
    Dependency to get MatchingService instance.
    
    Args:
        db: Database session
        
    Returns:
        MatchingService instance
    """
    return MatchingService(db=db)


# API Endpoints

@router.post(
    "/guilds/{guild_id}/join",
    response_model=JoinGuildResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Successfully joined guild"},
        404: {"model": ErrorResponse, "description": "Guild not found"},
        400: {"model": ErrorResponse, "description": "User already in guild or invalid request"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
    summary="Join a guild",
    description="Join a guild and get matched to a compatible squad or added to waiting pool. "
                "The system will automatically find the best squad match based on skill level, "
                "timezone, language, and vector similarity (> 0.7 threshold). "
                "If no compatible squad is available, user is added to waiting pool."
)
async def join_guild(
    guild_id: UUID = Path(..., description="Guild UUID to join"),
    current_user: User = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
    db: Session = Depends(get_db)
) -> JoinGuildResponse:
    """
    Join a guild and get matched to a squad or waiting pool.
    
    Implements Requirements:
    - 2.2: Interest area filtering for squad matching
    - 2.7: Waiting pool management
    
    Args:
        guild_id: Guild UUID to join
        current_user: Current authenticated user
        matching_service: Matching service instance
        db: Database session
        
    Returns:
        Join response with squad assignment or waiting pool status
        
    Raises:
        HTTPException: 404 if guild not found
        HTTPException: 400 if user already in guild
        HTTPException: 401 if not authenticated
    """
    try:
        # Check if user has profile
        if not current_user.profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile not found. Please complete onboarding first."
            )
        
        # Find compatible squads
        squad_matches = matching_service.find_squad_matches(
            user_id=current_user.id,
            guild_id=guild_id
        )
        
        # If compatible squad found, add user to best match
        if squad_matches:
            best_match = squad_matches[0]  # Already sorted by similarity
            squad_id = UUID(best_match["squad_id"])
            
            try:
                squad = matching_service.add_member_to_squad(
                    squad_id=squad_id,
                    user_id=current_user.id
                )
                
                return JoinGuildResponse(
                    success=True,
                    message="Successfully joined guild and assigned to squad",
                    squad_assigned=True,
                    squad_id=str(squad.id),
                    squad_name=squad.name,
                    in_waiting_pool=False
                )
            except ValueError as e:
                # Squad might have filled up, try next match or waiting pool
                if len(squad_matches) > 1:
                    # Try next best match
                    next_match = squad_matches[1]
                    squad_id = UUID(next_match["squad_id"])
                    squad = matching_service.add_member_to_squad(
                        squad_id=squad_id,
                        user_id=current_user.id
                    )
                    
                    return JoinGuildResponse(
                        success=True,
                        message="Successfully joined guild and assigned to squad",
                        squad_assigned=True,
                        squad_id=str(squad.id),
                        squad_name=squad.name,
                        in_waiting_pool=False
                    )
                else:
                    # No other matches, add to waiting pool
                    pass  # Fall through to waiting pool logic
        
        # No compatible squad found, add to waiting pool
        matching_service.add_to_waiting_pool(
            user_id=current_user.id,
            guild_id=guild_id
        )
        
        # Check for potential matches in waiting pool
        notification_result = matching_service.notify_waiting_pool_matches(guild_id)
        
        return JoinGuildResponse(
            success=True,
            message="Successfully joined guild. Added to waiting pool - you'll be notified when a compatible squad is available.",
            squad_assigned=False,
            squad_id=None,
            squad_name=None,
            in_waiting_pool=True
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error joining guild: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while joining guild"
        )


@router.get(
    "/guilds/{guild_id}/matches",
    response_model=SquadMatchesResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Squad matches retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Guild not found"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
    summary="Get squad matches for a guild",
    description="Get list of compatible squads in a guild for the current user. "
                "Returns squads with similarity score > 0.7 and available slots. "
                "Also includes waiting pool status."
)
async def get_squad_matches(
    guild_id: UUID = Path(..., description="Guild UUID"),
    current_user: User = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
    db: Session = Depends(get_db)
) -> SquadMatchesResponse:
    """
    Get compatible squad matches for user in a guild.
    
    Implements Requirement 2.2: Interest area filtering for squad matching.
    
    Args:
        guild_id: Guild UUID
        current_user: Current authenticated user
        matching_service: Matching service instance
        db: Database session
        
    Returns:
        Squad matches and waiting pool status
        
    Raises:
        HTTPException: 404 if guild not found
        HTTPException: 401 if not authenticated
    """
    try:
        # Check if user has profile
        if not current_user.profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile not found. Please complete onboarding first."
            )
        
        # Get guild info
        from app.models.guild import Guild, GuildMembership
        guild = db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild {guild_id} not found"
            )
        
        # Find compatible squads
        squad_matches = matching_service.find_squad_matches(
            user_id=current_user.id,
            guild_id=guild_id
        )
        
        # Check if user is in waiting pool
        guild_membership = db.query(GuildMembership).filter(
            GuildMembership.user_id == current_user.id,
            GuildMembership.guild_id == guild_id
        ).first()
        
        from app.models.squad import SquadMembership
        squad_membership = db.query(SquadMembership).join(Squad).filter(
            SquadMembership.user_id == current_user.id,
            Squad.guild_id == guild_id
        ).first()
        
        in_waiting_pool = guild_membership is not None and squad_membership is None
        
        # Get waiting pool size
        waiting_pool = matching_service.get_waiting_pool(guild_id)
        
        # Convert matches to response model
        match_responses = [
            SquadMatchResponse(**match)
            for match in squad_matches
        ]
        
        return SquadMatchesResponse(
            guild_id=str(guild.id),
            guild_name=guild.name,
            matches=match_responses,
            in_waiting_pool=in_waiting_pool,
            waiting_pool_size=len(waiting_pool)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error getting squad matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving squad matches"
        )


@router.get(
    "/guilds/{guild_id}/waiting-pool",
    response_model=WaitingPoolResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Waiting pool status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Guild not found"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
    },
    summary="Get waiting pool status for a guild",
    description="Get list of users waiting for squad assignment in a guild. "
                "Includes information about potential compatible groups."
)
async def get_waiting_pool_status(
    guild_id: UUID = Path(..., description="Guild UUID"),
    current_user: User = Depends(get_current_user),
    matching_service: MatchingService = Depends(get_matching_service),
    db: Session = Depends(get_db)
) -> WaitingPoolResponse:
    """
    Get waiting pool status for a guild.
    
    Implements Requirement 2.7: Waiting pool management.
    
    Args:
        guild_id: Guild UUID
        current_user: Current authenticated user
        matching_service: Matching service instance
        db: Database session
        
    Returns:
        Waiting pool status with user list and compatible groups
        
    Raises:
        HTTPException: 404 if guild not found
        HTTPException: 401 if not authenticated
    """
    try:
        # Get guild info
        from app.models.guild import Guild
        guild = db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild {guild_id} not found"
            )
        
        # Get waiting pool
        waiting_pool = matching_service.get_waiting_pool(guild_id)
        
        # Check for compatible groups
        notification_result = matching_service.notify_waiting_pool_matches(guild_id)
        
        # Convert to response model
        users = [
            WaitingPoolUser(**user)
            for user in waiting_pool
        ]
        
        return WaitingPoolResponse(
            guild_id=str(guild.id),
            guild_name=guild.name,
            waiting_pool_size=len(waiting_pool),
            users=users,
            compatible_groups_available=len(notification_result["compatible_groups"])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error getting waiting pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving waiting pool status"
        )
