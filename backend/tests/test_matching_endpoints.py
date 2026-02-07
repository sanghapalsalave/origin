"""
Unit tests for Matching API endpoints.

Tests:
- POST /matching/guilds/{guild_id}/join
- GET /matching/guilds/{guild_id}/matches
- GET /matching/guilds/{guild_id}/waiting-pool
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.models.user import User, UserProfile
from app.models.guild import Guild, GuildType
from app.models.squad import Squad, SquadStatus


client = TestClient(app)


class TestMatchingEndpoints:
    """Test suite for matching API endpoints."""
    
    @patch("app.api.dependencies.get_current_user")
    @patch("app.api.v1.endpoints.matching.get_matching_service")
    def test_join_guild_with_squad_match(
        self,
        mock_get_matching_service,
        mock_get_current_user
    ):
        """
        Test joining a guild when a compatible squad is available.
        
        Validates Requirement 2.2: Interest area filtering for squad matching.
        """
        # Setup mock user
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.profile = Mock(spec=UserProfile)
        mock_user.profile.display_name = "Test User"
        mock_get_current_user.return_value = mock_user
        
        # Setup mock matching service
        guild_id = uuid4()
        squad_id = uuid4()
        
        mock_service = Mock()
        mock_service.find_squad_matches.return_value = [
            {
                "squad_id": str(squad_id),
                "squad_name": "Test Squad",
                "member_count": 12,
                "average_similarity": 0.85,
                "status": "active",
                "available_slots": 3
            }
        ]
        
        mock_squad = Mock(spec=Squad)
        mock_squad.id = squad_id
        mock_squad.name = "Test Squad"
        mock_service.add_member_to_squad.return_value = mock_squad
        
        mock_get_matching_service.return_value = mock_service
        
        # Make request
        response = client.post(
            f"/api/v1/matching/guilds/{guild_id}/join",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["squad_assigned"] is True
        assert data["squad_id"] == str(squad_id)
        assert data["squad_name"] == "Test Squad"
        assert data["in_waiting_pool"] is False
    
    @patch("app.api.dependencies.get_current_user")
    @patch("app.api.v1.endpoints.matching.get_matching_service")
    def test_join_guild_no_match_waiting_pool(
        self,
        mock_get_matching_service,
        mock_get_current_user
    ):
        """
        Test joining a guild when no compatible squad is available.
        
        Validates Requirement 2.7: Waiting pool management.
        """
        # Setup mock user
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.profile = Mock(spec=UserProfile)
        mock_user.profile.display_name = "Test User"
        mock_get_current_user.return_value = mock_user
        
        # Setup mock matching service
        guild_id = uuid4()
        
        mock_service = Mock()
        mock_service.find_squad_matches.return_value = []  # No matches
        mock_service.add_to_waiting_pool.return_value = True
        mock_service.notify_waiting_pool_matches.return_value = {
            "compatible_groups": [],
            "notifications_sent": 0,
            "users_notified": []
        }
        
        mock_get_matching_service.return_value = mock_service
        
        # Make request
        response = client.post(
            f"/api/v1/matching/guilds/{guild_id}/join",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["squad_assigned"] is False
        assert data["squad_id"] is None
        assert data["in_waiting_pool"] is True
        assert "waiting pool" in data["message"].lower()
    
    @patch("app.api.dependencies.get_current_user")
    @patch("app.api.v1.endpoints.matching.get_matching_service")
    @patch("app.api.v1.endpoints.matching.get_db")
    def test_get_squad_matches(
        self,
        mock_get_db,
        mock_get_matching_service,
        mock_get_current_user
    ):
        """
        Test getting squad matches for a guild.
        
        Validates Requirement 2.2: Interest area filtering for squad matching.
        """
        # Setup mock user
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.profile = Mock(spec=UserProfile)
        mock_user.profile.display_name = "Test User"
        mock_get_current_user.return_value = mock_user
        
        # Setup mock database
        guild_id = uuid4()
        mock_guild = Mock(spec=Guild)
        mock_guild.id = guild_id
        mock_guild.name = "Test Guild"
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_guild
        mock_get_db.return_value = mock_db
        
        # Setup mock matching service
        squad_id = uuid4()
        mock_service = Mock()
        mock_service.find_squad_matches.return_value = [
            {
                "squad_id": str(squad_id),
                "squad_name": "Test Squad",
                "member_count": 13,
                "average_similarity": 0.82,
                "status": "active",
                "available_slots": 2
            }
        ]
        mock_service.get_waiting_pool.return_value = []
        
        mock_get_matching_service.return_value = mock_service
        
        # Make request
        response = client.get(
            f"/api/v1/matching/guilds/{guild_id}/matches",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["guild_id"] == str(guild_id)
        assert data["guild_name"] == "Test Guild"
        assert len(data["matches"]) == 1
        assert data["matches"][0]["squad_id"] == str(squad_id)
        assert data["matches"][0]["average_similarity"] == 0.82
        assert data["waiting_pool_size"] == 0
    
    @patch("app.api.dependencies.get_current_user")
    @patch("app.api.v1.endpoints.matching.get_matching_service")
    @patch("app.api.v1.endpoints.matching.get_db")
    def test_get_waiting_pool_status(
        self,
        mock_get_db,
        mock_get_matching_service,
        mock_get_current_user
    ):
        """
        Test getting waiting pool status for a guild.
        
        Validates Requirement 2.7: Waiting pool management.
        """
        # Setup mock user
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.profile = Mock(spec=UserProfile)
        mock_get_current_user.return_value = mock_user
        
        # Setup mock database
        guild_id = uuid4()
        mock_guild = Mock(spec=Guild)
        mock_guild.id = guild_id
        mock_guild.name = "Test Guild"
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_guild
        mock_get_db.return_value = mock_db
        
        # Setup mock matching service
        waiting_user_id = uuid4()
        mock_service = Mock()
        mock_service.get_waiting_pool.return_value = [
            {
                "user_id": str(waiting_user_id),
                "display_name": "Waiting User",
                "skill_level": 5,
                "interest_area": "Python Development",
                "timezone": "America/New_York",
                "language": "en",
                "joined_guild_at": "2024-01-15T10:30:00Z"
            }
        ]
        mock_service.notify_waiting_pool_matches.return_value = {
            "compatible_groups": [],
            "notifications_sent": 0,
            "users_notified": []
        }
        
        mock_get_matching_service.return_value = mock_service
        
        # Make request
        response = client.get(
            f"/api/v1/matching/guilds/{guild_id}/waiting-pool",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["guild_id"] == str(guild_id)
        assert data["guild_name"] == "Test Guild"
        assert data["waiting_pool_size"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["user_id"] == str(waiting_user_id)
        assert data["users"][0]["display_name"] == "Waiting User"
        assert data["compatible_groups_available"] == 0
    
    @patch("app.api.dependencies.get_current_user")
    def test_join_guild_without_profile_fails(self, mock_get_current_user):
        """
        Test that joining a guild without a profile returns 400 error.
        """
        # Setup mock user without profile
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.profile = None  # No profile
        mock_get_current_user.return_value = mock_user
        
        guild_id = uuid4()
        
        # Make request
        response = client.post(
            f"/api/v1/matching/guilds/{guild_id}/join",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "profile not found" in response.json()["detail"].lower()
    
    def test_join_guild_without_auth_fails(self):
        """
        Test that joining a guild without authentication returns 401 error.
        """
        guild_id = uuid4()
        
        # Make request without auth header
        response = client.post(f"/api/v1/matching/guilds/{guild_id}/join")
        
        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
