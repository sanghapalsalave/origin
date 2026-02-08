"""
Tests for Guild Master weekly syllabus update functionality.

Tests Requirement 3.5: Update syllabus at least once per week.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.guild_master_service import GuildMasterService
from app.models.squad import Squad, SquadStatus
from app.models.guild import Guild, GuildType
from app.models.user import User, UserProfile
from app.models.syllabus import Syllabus, SyllabusDay, Task, Resource, TaskType, ResourceType


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('app.services.guild_master_service.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock response for weekly update
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "days": [
                {
                    "day_number": 8,
                    "title": "Updated Day 8",
                    "learning_objectives": ["Updated objective 1"],
                    "tasks": [
                        {
                            "title": "Updated Task",
                            "description": "Updated description",
                            "task_type": "reading",
                            "estimated_minutes": 45,
                            "required": true,
                            "order_index": 0
                        }
                    ],
                    "resources": [
                        {
                            "title": "Updated Resource",
                            "url": "https://example.com/updated",
                            "resource_type": "article",
                            "description": "Updated resource",
                            "estimated_minutes": 20
                        }
                    ]
                }
            ]
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client


def test_update_syllabus_weekly_success(db_session: Session, mock_openai_client):
    """Test successful weekly syllabus update."""
    # Create guild
    guild = Guild(
        id=uuid4(),
        name="Python Mastery",
        interest_area="Python Programming",
        guild_type=GuildType.PUBLIC
    )
    db_session.add(guild)
    
    # Create squad
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Squad Alpha",
        status=SquadStatus.ACTIVE,
        member_count=12,
        current_day=7
    )
    db_session.add(squad)
    
    # Create syllabus (8 days old)
    old_date = datetime.utcnow() - timedelta(days=8)
    syllabus = Syllabus(
        id=uuid4(),
        squad_id=squad.id,
        version=1,
        learning_objectives=["Learn Python"],
        difficulty_level=5,
        estimated_hours_per_day=2.5,
        is_active=True,
        created_at=old_date,
        last_updated=old_date
    )
    db_session.add(syllabus)
    
    # Create syllabus days
    for day_num in range(1, 31):
        day = SyllabusDay(
            id=uuid4(),
            syllabus_id=syllabus.id,
            day_number=day_num,
            title=f"Day {day_num}",
            learning_objectives=[f"Objective {day_num}"],
            is_unlocked=(day_num <= 7),
            completion_count=6 if day_num <= 7 else 0
        )
        db_session.add(day)
        
        # Add a task to day 8 that will be replaced
        if day_num == 8:
            task = Task(
                id=uuid4(),
                syllabus_day_id=day.id,
                title="Old Task",
                description="Old description",
                task_type=TaskType.READING,
                estimated_minutes=60,
                required=True,
                order_index=0
            )
            db_session.add(task)
    
    squad.current_syllabus_id = syllabus.id
    db_session.commit()
    
    # Test weekly update
    service = GuildMasterService(db_session)
    updated_syllabus = service.update_syllabus_weekly(squad.id)
    
    assert updated_syllabus is not None
    assert updated_syllabus.id == syllabus.id
    assert updated_syllabus.last_updated > old_date
    
    # Verify day 8 was updated
    day_8 = db_session.query(SyllabusDay).filter(
        SyllabusDay.syllabus_id == syllabus.id,
        SyllabusDay.day_number == 8
    ).first()
    
    assert day_8.title == "Updated Day 8"
    assert "Updated objective 1" in day_8.learning_objectives
    
    # Verify tasks were updated
    tasks = db_session.query(Task).filter(Task.syllabus_day_id == day_8.id).all()
    assert len(tasks) == 1
    assert tasks[0].title == "Updated Task"
    assert tasks[0].estimated_minutes == 45


def test_update_syllabus_weekly_not_needed(db_session: Session, mock_openai_client):
    """Test that update is skipped if less than 7 days since last update."""
    # Create guild
    guild = Guild(
        id=uuid4(),
        name="Python Mastery",
        interest_area="Python Programming",
        guild_type=GuildType.PUBLIC
    )
    db_session.add(guild)
    
    # Create squad
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Squad Alpha",
        status=SquadStatus.ACTIVE,
        member_count=12,
        current_day=5
    )
    db_session.add(squad)
    
    # Create syllabus (only 3 days old)
    recent_date = datetime.utcnow() - timedelta(days=3)
    syllabus = Syllabus(
        id=uuid4(),
        squad_id=squad.id,
        version=1,
        learning_objectives=["Learn Python"],
        difficulty_level=5,
        estimated_hours_per_day=2.5,
        is_active=True,
        created_at=recent_date,
        last_updated=recent_date
    )
    db_session.add(syllabus)
    
    squad.current_syllabus_id = syllabus.id
    db_session.commit()
    
    # Test weekly update
    service = GuildMasterService(db_session)
    result = service.update_syllabus_weekly(squad.id)
    
    # Should return None since update not needed
    assert result is None
    
    # Verify OpenAI was not called
    mock_openai_client.chat.completions.create.assert_not_called()


def test_update_syllabus_weekly_triggers_pivot(db_session: Session, mock_openai_client):
    """Test that pivot is triggered instead of update if completion is low."""
    # Create guild
    guild = Guild(
        id=uuid4(),
        name="Python Mastery",
        interest_area="Python Programming",
        guild_type=GuildType.PUBLIC
    )
    db_session.add(guild)
    
    # Create squad
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Squad Alpha",
        status=SquadStatus.ACTIVE,
        member_count=12,
        current_day=7
    )
    db_session.add(squad)
    
    # Create syllabus (8 days old)
    old_date = datetime.utcnow() - timedelta(days=8)
    syllabus = Syllabus(
        id=uuid4(),
        squad_id=squad.id,
        version=1,
        learning_objectives=["Learn Python"],
        difficulty_level=5,
        estimated_hours_per_day=2.5,
        is_active=True,
        created_at=old_date,
        last_updated=old_date
    )
    db_session.add(syllabus)
    
    # Create syllabus days with low completion (< 60%)
    for day_num in range(1, 31):
        day = SyllabusDay(
            id=uuid4(),
            syllabus_id=syllabus.id,
            day_number=day_num,
            title=f"Day {day_num}",
            learning_objectives=[f"Objective {day_num}"],
            is_unlocked=(day_num <= 7),
            completion_count=5 if day_num <= 7 else 0  # 5/12 = 41.7% < 60%
        )
        db_session.add(day)
    
    squad.current_syllabus_id = syllabus.id
    db_session.commit()
    
    # Mock pivot response
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = '''
    {
        "learning_objectives": ["Pivoted objectives"],
        "estimated_hours_per_day": 2.0,
        "days": []
    }
    '''
    
    # Test weekly update
    service = GuildMasterService(db_session)
    result = service.update_syllabus_weekly(squad.id)
    
    # Should trigger pivot instead
    assert result is not None
    assert result.version == 2  # Pivoted version
    assert result.pivot_reason == "Low completion rate detected during weekly update"


def test_update_syllabus_weekly_no_syllabus(db_session: Session, mock_openai_client):
    """Test update when squad has no syllabus."""
    # Create guild
    guild = Guild(
        id=uuid4(),
        name="Python Mastery",
        interest_area="Python Programming",
        guild_type=GuildType.PUBLIC
    )
    db_session.add(guild)
    
    # Create squad without syllabus
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Squad Alpha",
        status=SquadStatus.ACTIVE,
        member_count=12,
        current_day=0
    )
    db_session.add(squad)
    db_session.commit()
    
    # Test weekly update
    service = GuildMasterService(db_session)
    result = service.update_syllabus_weekly(squad.id)
    
    # Should return None
    assert result is None


def test_update_syllabus_weekly_squad_not_found(db_session: Session, mock_openai_client):
    """Test update with non-existent squad."""
    service = GuildMasterService(db_session)
    
    with pytest.raises(ValueError, match="Squad .* not found"):
        service.update_syllabus_weekly(uuid4())


def test_update_syllabus_weekly_skips_completed_days(db_session: Session, mock_openai_client):
    """Test that update only modifies future days, not completed ones."""
    # Create guild
    guild = Guild(
        id=uuid4(),
        name="Python Mastery",
        interest_area="Python Programming",
        guild_type=GuildType.PUBLIC
    )
    db_session.add(guild)
    
    # Create squad
    squad = Squad(
        id=uuid4(),
        guild_id=guild.id,
        name="Squad Alpha",
        status=SquadStatus.ACTIVE,
        member_count=12,
        current_day=7
    )
    db_session.add(squad)
    
    # Create syllabus (8 days old)
    old_date = datetime.utcnow() - timedelta(days=8)
    syllabus = Syllabus(
        id=uuid4(),
        squad_id=squad.id,
        version=1,
        learning_objectives=["Learn Python"],
        difficulty_level=5,
        estimated_hours_per_day=2.5,
        is_active=True,
        created_at=old_date,
        last_updated=old_date
    )
    db_session.add(syllabus)
    
    # Create syllabus days
    for day_num in range(1, 31):
        day = SyllabusDay(
            id=uuid4(),
            syllabus_id=syllabus.id,
            day_number=day_num,
            title=f"Original Day {day_num}",
            learning_objectives=[f"Original Objective {day_num}"],
            is_unlocked=(day_num <= 7),
            completion_count=6 if day_num <= 7 else 0
        )
        db_session.add(day)
    
    squad.current_syllabus_id = syllabus.id
    db_session.commit()
    
    # Mock response that tries to update day 5 (already completed)
    mock_openai_client.chat.completions.create.return_value.choices[0].message.content = '''
    {
        "days": [
            {
                "day_number": 5,
                "title": "Should Not Update",
                "learning_objectives": ["Should not appear"],
                "tasks": [],
                "resources": []
            }
        ]
    }
    '''
    
    # Test weekly update
    service = GuildMasterService(db_session)
    service.update_syllabus_weekly(squad.id)
    
    # Verify day 5 was NOT updated
    day_5 = db_session.query(SyllabusDay).filter(
        SyllabusDay.syllabus_id == syllabus.id,
        SyllabusDay.day_number == 5
    ).first()
    
    assert day_5.title == "Original Day 5"
    assert day_5.learning_objectives == ["Original Objective 5"]
