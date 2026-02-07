"""
Unit tests for Squad and SquadMembership models.

Tests squad creation, status transitions, relationships, and membership tracking.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.models.squad import Squad, SquadMembership, SquadStatus


class TestSquadModel:
    """Test cases for Squad model."""
    
    def test_squad_creation_forming(self):
        """Test basic squad creation in FORMING status."""
        guild_id = uuid4()
        squad = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Alpha Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.FORMING,
            member_count=0,
            current_day=0,
            average_completion_rate=0.0,
            average_skill_level=0.0
        )
        
        assert squad.name == "Alpha Squad"
        assert squad.guild_id == guild_id
        assert squad.status == SquadStatus.FORMING
        assert squad.member_count == 0
        assert squad.current_day == 0
        assert squad.average_completion_rate == 0.0
        assert squad.average_skill_level == 0.0
    
    def test_squad_creation_active(self):
        """Test squad creation in ACTIVE status with learning progress."""
        guild_id = uuid4()
        syllabus_id = uuid4()
        start_date = datetime.utcnow()
        
        squad = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Beta Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.ACTIVE,
            member_count=12,
            current_syllabus_id=syllabus_id,
            syllabus_start_date=start_date,
            current_day=5,
            average_completion_rate=0.75,
            average_skill_level=6.5
        )
        
        assert squad.status == SquadStatus.ACTIVE
        assert squad.member_count == 12
        assert squad.current_syllabus_id == syllabus_id
        assert squad.syllabus_start_date == start_date
        assert squad.current_day == 5
        assert squad.average_completion_rate == 0.75
        assert squad.average_skill_level == 6.5
    
    def test_squad_creation_completed(self):
        """Test squad creation in COMPLETED status."""
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Gamma Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.COMPLETED,
            member_count=14,
            current_day=30
        )
        
        assert squad.status == SquadStatus.COMPLETED
        assert squad.current_day == 30
    
    def test_squad_status_enum_values(self):
        """Test that SquadStatus enum has correct values."""
        assert SquadStatus.FORMING.value == "forming"
        assert SquadStatus.ACTIVE.value == "active"
        assert SquadStatus.COMPLETED.value == "completed"
    
    def test_squad_default_values(self):
        """Test that squad has correct default values."""
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Test Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.FORMING,
            member_count=0,
            current_day=0,
            average_completion_rate=0.0,
            average_skill_level=0.0
        )
        
        assert squad.status == SquadStatus.FORMING
        assert squad.member_count == 0
        assert squad.current_day == 0
        assert squad.average_completion_rate == 0.0
        assert squad.average_skill_level == 0.0
        assert squad.current_syllabus_id is None
        assert squad.syllabus_start_date is None
        assert squad.chat_channel_id is None
    
    def test_squad_with_chat_channel(self):
        """Test squad with chat channel ID."""
        chat_channel_id = "firebase_channel_12345"
        
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Chat Squad",
            created_at=datetime.utcnow(),
            chat_channel_id=chat_channel_id
        )
        
        assert squad.chat_channel_id == chat_channel_id
    
    def test_squad_member_count_range(self):
        """Test squad with various member counts (0-15)."""
        # Test valid member counts
        for count in range(0, 16):
            squad = Squad(
                id=uuid4(),
                guild_id=uuid4(),
                name=f"Squad {count}",
                created_at=datetime.utcnow(),
                member_count=count
            )
            assert squad.member_count == count
    
    def test_squad_current_day_range(self):
        """Test squad with various current day values (0-30)."""
        # Test valid day values
        for day in range(0, 31):
            squad = Squad(
                id=uuid4(),
                guild_id=uuid4(),
                name=f"Squad Day {day}",
                created_at=datetime.utcnow(),
                current_day=day
            )
            assert squad.current_day == day
    
    def test_squad_completion_rate_range(self):
        """Test squad with various completion rates (0.0-1.0)."""
        rates = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for rate in rates:
            squad = Squad(
                id=uuid4(),
                guild_id=uuid4(),
                name=f"Squad Rate {rate}",
                created_at=datetime.utcnow(),
                average_completion_rate=rate
            )
            assert squad.average_completion_rate == rate
    
    def test_squad_skill_level_range(self):
        """Test squad with various average skill levels (1-10)."""
        levels = [1.0, 3.5, 5.0, 7.5, 10.0]
        
        for level in levels:
            squad = Squad(
                id=uuid4(),
                guild_id=uuid4(),
                name=f"Squad Level {level}",
                created_at=datetime.utcnow(),
                average_skill_level=level
            )
            assert squad.average_skill_level == level
    
    def test_squad_repr(self):
        """Test squad string representation."""
        squad_id = uuid4()
        squad = Squad(
            id=squad_id,
            guild_id=uuid4(),
            name="Alpha Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.ACTIVE,
            member_count=13
        )
        
        repr_str = repr(squad)
        assert "Squad" in repr_str
        assert str(squad_id) in repr_str
        assert "Alpha Squad" in repr_str
        assert "active" in repr_str
        assert "13" in repr_str
    
    def test_squad_status_transitions(self):
        """Test squad status can transition through lifecycle."""
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Lifecycle Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.FORMING,
            member_count=10
        )
        
        # Initially forming
        assert squad.status == SquadStatus.FORMING
        
        # Transition to active when reaching 12 members
        squad.status = SquadStatus.ACTIVE
        squad.member_count = 12
        assert squad.status == SquadStatus.ACTIVE
        assert squad.member_count == 12
        
        # Transition to completed after 30 days
        squad.status = SquadStatus.COMPLETED
        squad.current_day = 30
        assert squad.status == SquadStatus.COMPLETED
        assert squad.current_day == 30
    
    def test_squad_minimum_active_members(self):
        """Test squad with minimum active member count (12)."""
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Min Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.ACTIVE,
            member_count=12
        )
        
        assert squad.member_count == 12
        assert squad.status == SquadStatus.ACTIVE
    
    def test_squad_maximum_active_members(self):
        """Test squad with maximum active member count (15)."""
        squad = Squad(
            id=uuid4(),
            guild_id=uuid4(),
            name="Max Squad",
            created_at=datetime.utcnow(),
            status=SquadStatus.ACTIVE,
            member_count=15
        )
        
        assert squad.member_count == 15
        assert squad.status == SquadStatus.ACTIVE


class TestSquadMembershipModel:
    """Test cases for SquadMembership model."""
    
    def test_squad_membership_creation(self):
        """Test basic squad membership creation."""
        user_id = uuid4()
        squad_id = uuid4()
        joined_at = datetime.utcnow()
        
        membership = SquadMembership(
            id=uuid4(),
            user_id=user_id,
            squad_id=squad_id,
            joined_at=joined_at
        )
        
        assert membership.user_id == user_id
        assert membership.squad_id == squad_id
        assert membership.joined_at == joined_at
    
    def test_squad_membership_repr(self):
        """Test squad membership string representation."""
        user_id = uuid4()
        squad_id = uuid4()
        
        membership = SquadMembership(
            id=uuid4(),
            user_id=user_id,
            squad_id=squad_id,
            joined_at=datetime.utcnow()
        )
        
        repr_str = repr(membership)
        assert "SquadMembership" in repr_str
        assert str(user_id) in repr_str
        assert str(squad_id) in repr_str
    
    def test_multiple_memberships_same_user(self):
        """Test that a user can have multiple squad memberships."""
        user_id = uuid4()
        squad1_id = uuid4()
        squad2_id = uuid4()
        
        membership1 = SquadMembership(
            id=uuid4(),
            user_id=user_id,
            squad_id=squad1_id,
            joined_at=datetime.utcnow()
        )
        
        membership2 = SquadMembership(
            id=uuid4(),
            user_id=user_id,
            squad_id=squad2_id,
            joined_at=datetime.utcnow()
        )
        
        assert membership1.user_id == membership2.user_id
        assert membership1.squad_id != membership2.squad_id
    
    def test_multiple_memberships_same_squad(self):
        """Test that a squad can have multiple user memberships."""
        squad_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()
        
        membership1 = SquadMembership(
            id=uuid4(),
            user_id=user1_id,
            squad_id=squad_id,
            joined_at=datetime.utcnow()
        )
        
        membership2 = SquadMembership(
            id=uuid4(),
            user_id=user2_id,
            squad_id=squad_id,
            joined_at=datetime.utcnow()
        )
        
        assert membership1.squad_id == membership2.squad_id
        assert membership1.user_id != membership2.user_id
    
    def test_squad_with_12_members(self):
        """Test creating 12 memberships for a squad (minimum active size)."""
        squad_id = uuid4()
        memberships = []
        
        for i in range(12):
            membership = SquadMembership(
                id=uuid4(),
                user_id=uuid4(),
                squad_id=squad_id,
                joined_at=datetime.utcnow()
            )
            memberships.append(membership)
        
        assert len(memberships) == 12
        # All memberships should have the same squad_id
        assert all(m.squad_id == squad_id for m in memberships)
        # All memberships should have unique user_ids
        user_ids = [m.user_id for m in memberships]
        assert len(user_ids) == len(set(user_ids))
    
    def test_squad_with_15_members(self):
        """Test creating 15 memberships for a squad (maximum active size)."""
        squad_id = uuid4()
        memberships = []
        
        for i in range(15):
            membership = SquadMembership(
                id=uuid4(),
                user_id=uuid4(),
                squad_id=squad_id,
                joined_at=datetime.utcnow()
            )
            memberships.append(membership)
        
        assert len(memberships) == 15
        # All memberships should have the same squad_id
        assert all(m.squad_id == squad_id for m in memberships)
        # All memberships should have unique user_ids
        user_ids = [m.user_id for m in memberships]
        assert len(user_ids) == len(set(user_ids))


class TestSquadRelationships:
    """Test cases for Squad relationships."""
    
    def test_squad_guild_relationship_setup(self):
        """Test that Squad and Guild can be linked."""
        guild_id = uuid4()
        
        squad = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Test Squad",
            created_at=datetime.utcnow()
        )
        
        # Verify the foreign key relationship
        assert squad.guild_id == guild_id
    
    def test_squad_membership_relationship_setup(self):
        """Test that Squad and SquadMembership can be linked."""
        squad_id = uuid4()
        user_id = uuid4()
        
        squad = Squad(
            id=squad_id,
            guild_id=uuid4(),
            name="Test Squad",
            created_at=datetime.utcnow()
        )
        
        membership = SquadMembership(
            id=uuid4(),
            user_id=user_id,
            squad_id=squad_id,
            joined_at=datetime.utcnow()
        )
        
        # Verify the foreign key relationship
        assert membership.squad_id == squad.id
    
    def test_multiple_squads_in_guild(self):
        """Test that a guild can have multiple squads."""
        guild_id = uuid4()
        
        squad1 = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Alpha Squad",
            created_at=datetime.utcnow()
        )
        
        squad2 = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Beta Squad",
            created_at=datetime.utcnow()
        )
        
        squad3 = Squad(
            id=uuid4(),
            guild_id=guild_id,
            name="Gamma Squad",
            created_at=datetime.utcnow()
        )
        
        # All squads should belong to the same guild
        assert squad1.guild_id == guild_id
        assert squad2.guild_id == guild_id
        assert squad3.guild_id == guild_id
        
        # Each squad should have a unique ID
        assert squad1.id != squad2.id != squad3.id
