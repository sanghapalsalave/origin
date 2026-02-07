"""
Unit tests for MatchingService.

Tests squad formation logic including:
- Squad creation with size constraints
- Squad activation at 12 members
- Member addition with compatibility checks
- Waiting pool management
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.matching_service import MatchingService
from app.models.user import User, UserProfile
from app.models.guild import Guild, GuildType, GuildMembership
from app.models.squad import Squad, SquadMembership, SquadStatus
from app.models.skill_assessment import VectorEmbedding


class TestMatchingService:
    """Test suite for MatchingService."""
    
    def test_create_new_squad_with_12_members_activates(self, db_session):
        """
        Test that creating a squad with exactly 12 members marks it as ACTIVE.
        
        Validates Requirement 2.5: Squad activation at threshold.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create 12 users with profiles and embeddings
        user_ids = []
        for i in range(12):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en",
                learning_velocity=1.0
            )
            db_session.add(profile)
            
            embedding = VectorEmbedding(
                user_id=user.id,
                pinecone_id=f"user_{user.id}",
                skill_level=5,
                learning_velocity=1.0,
                timezone_offset=-5.0,
                language_code="en",
                interest_area="Python Development"
            )
            db_session.add(embedding)
            
            user_ids.append(user.id)
        
        db_session.commit()
        
        # Mock Pinecone compatibility check
        with patch.object(service, '_verify_member_compatibility', return_value=True):
            # Create squad with 12 members
            squad = service.create_new_squad(
                guild_id=guild.id,
                initial_members=user_ids,
                squad_name="Test Squad"
            )
        
        # Assertions
        assert squad.status == SquadStatus.ACTIVE
        assert squad.member_count == 12
        assert squad.guild_id == guild.id
        assert len(squad.memberships) == 12
    
    def test_create_new_squad_with_less_than_12_fails(self, db_session):
        """
        Test that creating a squad with less than 12 members raises ValueError.
        
        Validates Requirement 2.6: Squad size constraints.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create only 10 users
        user_ids = []
        for i in range(10):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en"
            )
            db_session.add(profile)
            
            user_ids.append(user.id)
        
        db_session.commit()
        
        # Attempt to create squad with 10 members
        with pytest.raises(ValueError, match="Cannot create squad with 10 members"):
            service.create_new_squad(
                guild_id=guild.id,
                initial_members=user_ids
            )
    
    def test_create_new_squad_with_more_than_15_fails(self, db_session):
        """
        Test that creating a squad with more than 15 members raises ValueError.
        
        Validates Requirement 2.6: Squad size constraints.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create 16 users
        user_ids = []
        for i in range(16):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en"
            )
            db_session.add(profile)
            
            user_ids.append(user.id)
        
        db_session.commit()
        
        # Attempt to create squad with 16 members
        with pytest.raises(ValueError, match="Cannot create squad with 16 members"):
            service.create_new_squad(
                guild_id=guild.id,
                initial_members=user_ids
            )
    
    def test_add_member_to_squad_activates_at_12(self, db_session):
        """
        Test that adding a member to reach 12 total activates the squad.
        
        Validates Requirement 2.5: Squad activation at threshold.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create squad with 11 members (FORMING status)
        squad = Squad(
            guild_id=guild.id,
            name="Test Squad",
            status=SquadStatus.FORMING,
            member_count=11,
            average_skill_level=5.0
        )
        db_session.add(squad)
        db_session.flush()
        
        # Create 11 existing members
        for i in range(11):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en"
            )
            db_session.add(profile)
            
            membership = SquadMembership(
                user_id=user.id,
                squad_id=squad.id
            )
            db_session.add(membership)
        
        # Create 12th user
        new_user = User(
            email="user11@example.com",
            password_hash="hashed"
        )
        db_session.add(new_user)
        db_session.flush()
        
        new_profile = UserProfile(
            user_id=new_user.id,
            display_name="User 11",
            interest_area="Python Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en"
        )
        db_session.add(new_profile)
        
        embedding = VectorEmbedding(
            user_id=new_user.id,
            pinecone_id=f"user_{new_user.id}",
            skill_level=5,
            learning_velocity=1.0,
            timezone_offset=-5.0,
            language_code="en",
            interest_area="Python Development"
        )
        db_session.add(embedding)
        
        db_session.commit()
        
        # Mock compatibility check
        with patch.object(service, '_verify_member_compatibility', return_value=True):
            # Add 12th member
            updated_squad = service.add_member_to_squad(
                squad_id=squad.id,
                user_id=new_user.id
            )
        
        # Assertions
        assert updated_squad.status == SquadStatus.ACTIVE
        assert updated_squad.member_count == 12
    
    def test_add_member_to_full_squad_fails(self, db_session):
        """
        Test that adding a member to a full squad (15 members) raises ValueError.
        
        Validates Requirement 2.6: Squad size constraints.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create squad with 15 members (full)
        squad = Squad(
            guild_id=guild.id,
            name="Test Squad",
            status=SquadStatus.ACTIVE,
            member_count=15,
            average_skill_level=5.0
        )
        db_session.add(squad)
        db_session.flush()
        
        # Create new user to add
        new_user = User(
            email="newuser@example.com",
            password_hash="hashed"
        )
        db_session.add(new_user)
        db_session.flush()
        
        new_profile = UserProfile(
            user_id=new_user.id,
            display_name="New User",
            interest_area="Python Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en"
        )
        db_session.add(new_profile)
        db_session.commit()
        
        # Attempt to add to full squad
        with pytest.raises(ValueError, match="Squad .* is full"):
            service.add_member_to_squad(
                squad_id=squad.id,
                user_id=new_user.id
            )
    
    def test_get_waiting_pool(self, db_session):
        """
        Test retrieving users in the waiting pool for a guild.
        
        Validates Requirement 2.7: Waiting pool management.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create 5 users in guild
        guild_users = []
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en"
            )
            db_session.add(profile)
            
            # Add to guild
            membership = GuildMembership(
                user_id=user.id,
                guild_id=guild.id
            )
            db_session.add(membership)
            
            guild_users.append(user)
        
        # Create squad and add 2 users to it
        squad = Squad(
            guild_id=guild.id,
            name="Test Squad",
            status=SquadStatus.FORMING,
            member_count=2,
            average_skill_level=5.0
        )
        db_session.add(squad)
        db_session.flush()
        
        for i in range(2):
            squad_membership = SquadMembership(
                user_id=guild_users[i].id,
                squad_id=squad.id
            )
            db_session.add(squad_membership)
        
        db_session.commit()
        
        # Get waiting pool
        waiting_pool = service.get_waiting_pool(guild_id=guild.id)
        
        # Assertions
        assert len(waiting_pool) == 3  # 5 guild members - 2 in squad = 3 waiting
        waiting_user_ids = {user["user_id"] for user in waiting_pool}
        assert str(guild_users[2].id) in waiting_user_ids
        assert str(guild_users[3].id) in waiting_user_ids
        assert str(guild_users[4].id) in waiting_user_ids


@pytest.fixture
def db_session():
    """Create a mock database session for testing."""
    session = MagicMock(spec=Session)
    
    # Mock query behavior
    def mock_query(model):
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.join.return_value = query_mock
        query_mock.first.return_value = None
        query_mock.all.return_value = []
        query_mock.count.return_value = 0
        return query_mock
    
    session.query = mock_query
    session.add = MagicMock()
    session.flush = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    
    return session

    
    def test_notify_waiting_pool_with_insufficient_users(self, db_session):
        """
        Test that notification returns empty when waiting pool has < 12 users.
        
        Validates Requirement 2.7: Waiting pool management.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create only 8 users in waiting pool
        for i in range(8):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed"
            )
            db_session.add(user)
            db_session.flush()
            
            profile = UserProfile(
                user_id=user.id,
                display_name=f"User {i}",
                interest_area="Python Development",
                skill_level=5,
                timezone="America/New_York",
                preferred_language="en"
            )
            db_session.add(profile)
            
            # Add to guild (waiting pool)
            membership = GuildMembership(
                user_id=user.id,
                guild_id=guild.id
            )
            db_session.add(membership)
        
        db_session.commit()
        
        # Check for matches
        result = service.notify_waiting_pool_matches(guild_id=guild.id)
        
        # Assertions
        assert result["compatible_groups"] == []
        assert result["notifications_sent"] == 0
        assert result["users_notified"] == []
    
    def test_add_to_waiting_pool(self, db_session):
        """
        Test adding a user to the waiting pool.
        
        Validates Requirement 2.7: Waiting pool management.
        """
        # Setup
        service = MatchingService(db_session)
        
        # Create guild
        guild = Guild(
            name="Python Guild",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC
        )
        db_session.add(guild)
        db_session.flush()
        
        # Create user
        user = User(
            email="user@example.com",
            password_hash="hashed"
        )
        db_session.add(user)
        db_session.flush()
        
        profile = UserProfile(
            user_id=user.id,
            display_name="Test User",
            interest_area="Python Development",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en"
        )
        db_session.add(profile)
        db_session.commit()
        
        # Add to waiting pool
        result = service.add_to_waiting_pool(
            user_id=user.id,
            guild_id=guild.id
        )
        
        # Assertions
        assert result is True
        
        # Verify guild membership was created
        membership = db_session.query(GuildMembership).filter(
            GuildMembership.user_id == user.id,
            GuildMembership.guild_id == guild.id
        ).first()
        assert membership is not None
