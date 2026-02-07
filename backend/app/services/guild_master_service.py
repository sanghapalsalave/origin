"""
Guild Master AI Service

Provides AI-powered curriculum generation, syllabus management, and squad facilitation.

Implements Requirements:
- 3.1: Generate 30-day syllabus
- 3.2: Include daily objectives, tasks, and resources
- 3.3: Detect low completion rates
- 3.4: Pivot curriculum based on performance
"""
import logging
import json
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.models.squad import Squad
from app.models.user import User
from app.models.syllabus import Syllabus, SyllabusDay, Task, Resource, TaskType, ResourceType
from app.models.guild import Guild

logger = logging.getLogger(__name__)


class GuildMasterService:
    """Service for Guild Master AI operations."""
    
    def __init__(self, db: Session):
        """
        Initialize Guild Master service.
        
        Args:
            db: Database session
        """
        self.db = db
        
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured. Guild Master AI features will be limited.")
            self.client = None
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        logger.info("GuildMasterService initialized")
    
    def generate_syllabus(
        self,
        squad_id: UUID,
        custom_objectives: Optional[List[str]] = None
    ) -> Syllabus:
        """
        Generate 30-day learning roadmap for a squad.
        
        Implements Requirements:
        - 3.1: Generate 30-day syllabus
        - 3.2: Include daily objectives, tasks, and resources
        
        Args:
            squad_id: Squad ID
            custom_objectives: Optional custom learning objectives (for private guilds)
            
        Returns:
            Generated Syllabus object
            
        Raises:
            ValueError: If squad not found or OpenAI not configured
        """
        # Get squad and members
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Get guild
        guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()
        if not guild:
            raise ValueError(f"Guild {squad.guild_id} not found")
        
        # Get squad members with profiles
        members = []
        for membership in squad.memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if user and user.profile:
                members.append(user)
        
        if not members:
            raise ValueError(f"Squad {squad_id} has no members with profiles")
        
        # Analyze squad skill distribution
        skill_levels = [user.profile.skill_level for user in members]
        median_skill = sorted(skill_levels)[len(skill_levels) // 2]
        min_skill = min(skill_levels)
        max_skill = max(skill_levels)
        avg_skill = sum(skill_levels) / len(skill_levels)
        
        # Determine difficulty level
        difficulty_level = int(avg_skill)
        
        # Generate syllabus using LLM
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Build prompt
        prompt = self._build_syllabus_prompt(
            guild_name=guild.name,
            interest_area=guild.interest_area,
            squad_size=len(members),
            median_skill=median_skill,
            min_skill=min_skill,
            max_skill=max_skill,
            difficulty_level=difficulty_level,
            custom_objectives=custom_objectives or (guild.custom_objectives if hasattr(guild, 'custom_objectives') else None)
        )
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert curriculum designer creating personalized learning paths."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            syllabus_data = json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise ValueError(f"Failed to generate syllabus: {str(e)}")
        
        # Create syllabus in database
        syllabus = self._create_syllabus_from_data(
            squad_id=squad_id,
            syllabus_data=syllabus_data,
            difficulty_level=difficulty_level
        )
        
        # Update squad with syllabus
        squad.current_syllabus_id = syllabus.id
        squad.syllabus_start_date = datetime.utcnow()
        squad.current_day = 0
        
        self.db.commit()
        self.db.refresh(syllabus)
        
        logger.info(f"Generated syllabus {syllabus.id} for squad {squad_id}")
        
        return syllabus
    
    def _build_syllabus_prompt(
        self,
        guild_name: str,
        interest_area: str,
        squad_size: int,
        median_skill: int,
        min_skill: int,
        max_skill: int,
        difficulty_level: int,
        custom_objectives: Optional[List[str]] = None
    ) -> str:
        """Build prompt for syllabus generation."""
        
        custom_obj_text = ""
        if custom_objectives:
            custom_obj_text = f"\n\nCustom Learning Objectives:\n" + "\n".join(f"- {obj}" for obj in custom_objectives)
        
        prompt = f"""Generate a comprehensive 30-day learning syllabus for a squad in the "{guild_name}" guild.

Interest Area: {interest_area}
Squad Size: {squad_size} members
Skill Level Distribution:
- Median: {median_skill}/10
- Range: {min_skill}/10 to {max_skill}/10
- Target Difficulty: {difficulty_level}/10
{custom_obj_text}

Create a structured 30-day curriculum that:
1. Builds progressively from fundamentals to advanced topics
2. Includes daily learning objectives
3. Provides a mix of reading, coding exercises, and projects
4. Includes collaborative squad activities
5. Has milestone projects at days 10, 20, and 30
6. Accommodates the skill level range

Return a JSON object with this structure:
{{
  "learning_objectives": ["objective1", "objective2", ...],
  "estimated_hours_per_day": 2.5,
  "days": [
    {{
      "day_number": 1,
      "title": "Day title",
      "learning_objectives": ["objective1", "objective2"],
      "tasks": [
        {{
          "title": "Task title",
          "description": "Detailed description",
          "task_type": "reading|coding|project|quiz",
          "estimated_minutes": 60,
          "required": true,
          "order_index": 0
        }}
      ],
      "resources": [
        {{
          "title": "Resource title",
          "url": "https://example.com",
          "resource_type": "article|video|documentation|tutorial",
          "description": "Brief description",
          "estimated_minutes": 30
        }}
      ]
    }}
  ]
}}

Ensure exactly 30 days are included."""
        
        return prompt
    
    def _create_syllabus_from_data(
        self,
        squad_id: UUID,
        syllabus_data: Dict[str, Any],
        difficulty_level: int
    ) -> Syllabus:
        """Create syllabus and related objects from LLM response data."""
        
        # Create syllabus
        syllabus = Syllabus(
            squad_id=squad_id,
            version=1,
            learning_objectives=syllabus_data.get("learning_objectives", []),
            difficulty_level=difficulty_level,
            estimated_hours_per_day=syllabus_data.get("estimated_hours_per_day", 2.0),
            is_active=True
        )
        
        self.db.add(syllabus)
        self.db.flush()
        
        # Create days
        for day_data in syllabus_data.get("days", []):
            day_number = day_data.get("day_number", 1)
            
            # Calculate unlock date (day 1 unlocks immediately)
            unlock_date = datetime.utcnow() if day_number == 1 else None
            is_unlocked = day_number == 1
            
            syllabus_day = SyllabusDay(
                syllabus_id=syllabus.id,
                day_number=day_number,
                title=day_data.get("title", f"Day {day_number}"),
                learning_objectives=day_data.get("learning_objectives", []),
                unlock_date=unlock_date,
                is_unlocked=is_unlocked
            )
            
            self.db.add(syllabus_day)
            self.db.flush()
            
            # Create tasks
            for task_data in day_data.get("tasks", []):
                task = Task(
                    syllabus_day_id=syllabus_day.id,
                    title=task_data.get("title", "Untitled Task"),
                    description=task_data.get("description", ""),
                    task_type=TaskType(task_data.get("task_type", "reading")),
                    estimated_minutes=task_data.get("estimated_minutes", 60),
                    required=task_data.get("required", True),
                    order_index=task_data.get("order_index", 0)
                )
                self.db.add(task)
            
            # Create resources
            for resource_data in day_data.get("resources", []):
                resource = Resource(
                    syllabus_day_id=syllabus_day.id,
                    title=resource_data.get("title", "Untitled Resource"),
                    url=resource_data.get("url", ""),
                    resource_type=ResourceType(resource_data.get("resource_type", "article")),
                    description=resource_data.get("description"),
                    estimated_minutes=resource_data.get("estimated_minutes")
                )
                self.db.add(resource)
        
        return syllabus

    
    def pivot_syllabus(
        self,
        squad_id: UUID,
        reason: str
    ) -> Syllabus:
        """
        Adjust syllabus based on squad performance.
        
        Implements Requirements:
        - 3.3: Detect low completion rates
        - 3.4: Adjust difficulty and pacing
        
        Args:
            squad_id: Squad ID
            reason: Reason for pivot
            
        Returns:
            New pivoted Syllabus object
            
        Raises:
            ValueError: If squad or current syllabus not found
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        if not squad.current_syllabus_id:
            raise ValueError(f"Squad {squad_id} has no active syllabus")
        
        # Get current syllabus
        current_syllabus = self.db.query(Syllabus).filter(
            Syllabus.id == squad.current_syllabus_id
        ).first()
        
        if not current_syllabus:
            raise ValueError(f"Current syllabus not found")
        
        # Get guild
        guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()
        
        # Analyze current progress
        completed_days = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == current_syllabus.id,
            SyllabusDay.completion_count >= squad.member_count * 0.5
        ).count()
        
        # Build pivot prompt
        prompt = f"""The squad is struggling with the current syllabus. Generate an adjusted version.

Original Difficulty: {current_syllabus.difficulty_level}/10
Days Completed: {completed_days}/{squad.current_day}
Reason for Pivot: {reason}

Adjust the remaining days to:
1. Reduce difficulty by 1-2 levels
2. Extend time for complex concepts
3. Add more examples and practice
4. Simplify project requirements

Continue from day {squad.current_day + 1} to day 30.
Return JSON with same structure as before."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert curriculum designer adjusting learning paths."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            pivot_data = json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error pivoting syllabus: {str(e)}")
            raise ValueError(f"Failed to pivot syllabus: {str(e)}")
        
        # Deactivate current syllabus
        current_syllabus.is_active = False
        
        # Create new syllabus
        new_difficulty = max(1, current_syllabus.difficulty_level - 1)
        new_syllabus = self._create_syllabus_from_data(
            squad_id=squad_id,
            syllabus_data=pivot_data,
            difficulty_level=new_difficulty
        )
        
        new_syllabus.version = current_syllabus.version + 1
        new_syllabus.pivot_reason = reason
        new_syllabus.previous_syllabus_id = current_syllabus.id
        
        # Update squad
        squad.current_syllabus_id = new_syllabus.id
        
        self.db.commit()
        self.db.refresh(new_syllabus)
        
        logger.info(f"Pivoted syllabus for squad {squad_id}. New version: {new_syllabus.version}")
        
        return new_syllabus
    
    def check_pivot_needed(self, squad_id: UUID) -> bool:
        """
        Check if syllabus pivot is needed based on completion rates.
        
        Implements Requirement 3.3: Trigger pivot when completion < 60% for 3 consecutive days.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            True if pivot is needed
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad or not squad.current_syllabus_id:
            return False
        
        # Get last 3 days
        recent_days = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == squad.current_syllabus_id,
            SyllabusDay.day_number <= squad.current_day,
            SyllabusDay.day_number > squad.current_day - 3
        ).order_by(SyllabusDay.day_number.desc()).limit(3).all()
        
        if len(recent_days) < 3:
            return False
        
        # Check if all 3 days have < 60% completion
        threshold = squad.member_count * 0.6
        low_completion_days = sum(1 for day in recent_days if day.completion_count < threshold)
        
        return low_completion_days >= 3
    
    def unlock_next_day(self, squad_id: UUID) -> Optional[SyllabusDay]:
        """
        Unlock next day's content for squad.
        
        Implements Requirement 3.6: Unlock content on completion.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            Unlocked SyllabusDay or None
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad or not squad.current_syllabus_id:
            return None
        
        next_day_number = squad.current_day + 1
        if next_day_number > 30:
            return None
        
        next_day = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == squad.current_syllabus_id,
            SyllabusDay.day_number == next_day_number
        ).first()
        
        if next_day and not next_day.is_unlocked:
            next_day.is_unlocked = True
            next_day.unlock_date = datetime.utcnow()
            squad.current_day = next_day_number
            
            self.db.commit()
            self.db.refresh(next_day)
            
            logger.info(f"Unlocked day {next_day_number} for squad {squad_id}")
            
            return next_day
        
        return None
