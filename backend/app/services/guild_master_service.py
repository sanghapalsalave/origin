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
    
    def update_syllabus_weekly(self, squad_id: UUID) -> Optional[Syllabus]:
        """
        Update syllabus based on weekly squad progress.
        
        Implements Requirement 3.5: Update syllabus at least once per week.
        
        This method checks if a week has passed since the last update and
        generates an updated syllabus based on squad progress and performance.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            Updated Syllabus object or None if update not needed
            
        Raises:
            ValueError: If squad or syllabus not found
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        if not squad.current_syllabus_id:
            logger.warning(f"Squad {squad_id} has no active syllabus")
            return None
        
        # Get current syllabus
        current_syllabus = self.db.query(Syllabus).filter(
            Syllabus.id == squad.current_syllabus_id
        ).first()
        
        if not current_syllabus:
            raise ValueError(f"Current syllabus {squad.current_syllabus_id} not found")
        
        # Check if update is needed (7 days since last update)
        last_update = current_syllabus.last_updated or current_syllabus.created_at
        days_since_update = (datetime.utcnow() - last_update).days
        
        if days_since_update < 7:
            logger.info(f"Syllabus for squad {squad_id} was updated {days_since_update} days ago. No update needed.")
            return None
        
        # Get squad progress metrics
        completed_days = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == current_syllabus.id,
            SyllabusDay.completion_count >= squad.member_count * 0.5
        ).count()
        
        completion_rate = completed_days / squad.current_day if squad.current_day > 0 else 0
        
        # Check if pivot is needed instead
        if self.check_pivot_needed(squad_id):
            logger.info(f"Squad {squad_id} needs pivot instead of weekly update")
            return self.pivot_syllabus(
                squad_id=squad_id,
                reason="Low completion rate detected during weekly update"
            )
        
        # Get guild for context
        guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()
        
        # Build update prompt
        prompt = f"""Review and update the learning syllabus for a squad in the "{guild.name}" guild.

Current Progress:
- Days Completed: {completed_days}/{squad.current_day}
- Completion Rate: {completion_rate:.1%}
- Current Difficulty: {current_syllabus.difficulty_level}/10

Analyze the squad's progress and make adjustments to the remaining days (day {squad.current_day + 1} to day 30):
1. Reinforce concepts where completion is low
2. Add supplementary resources for struggling topics
3. Adjust pacing if squad is ahead or behind schedule
4. Ensure project milestones are appropriately challenging

Return a JSON object with the updated syllabus structure for the remaining days."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert curriculum designer reviewing and updating learning paths."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            update_data = json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error updating syllabus: {str(e)}")
            raise ValueError(f"Failed to update syllabus: {str(e)}")
        
        # Update the syllabus timestamp
        current_syllabus.last_updated = datetime.utcnow()
        
        # Update remaining days with new content
        for day_data in update_data.get("days", []):
            day_number = day_data.get("day_number")
            if day_number <= squad.current_day:
                continue  # Skip already completed days
            
            # Find existing day
            existing_day = self.db.query(SyllabusDay).filter(
                SyllabusDay.syllabus_id == current_syllabus.id,
                SyllabusDay.day_number == day_number
            ).first()
            
            if existing_day:
                # Update day content
                existing_day.title = day_data.get("title", existing_day.title)
                existing_day.learning_objectives = day_data.get("learning_objectives", existing_day.learning_objectives)
                
                # Delete old tasks and resources
                self.db.query(Task).filter(Task.syllabus_day_id == existing_day.id).delete()
                self.db.query(Resource).filter(Resource.syllabus_day_id == existing_day.id).delete()
                
                # Create new tasks
                for task_data in day_data.get("tasks", []):
                    task = Task(
                        syllabus_day_id=existing_day.id,
                        title=task_data.get("title", "Untitled Task"),
                        description=task_data.get("description", ""),
                        task_type=TaskType(task_data.get("task_type", "reading")),
                        estimated_minutes=task_data.get("estimated_minutes", 60),
                        required=task_data.get("required", True),
                        order_index=task_data.get("order_index", 0)
                    )
                    self.db.add(task)
                
                # Create new resources
                for resource_data in day_data.get("resources", []):
                    resource = Resource(
                        syllabus_day_id=existing_day.id,
                        title=resource_data.get("title", "Untitled Resource"),
                        url=resource_data.get("url", ""),
                        resource_type=ResourceType(resource_data.get("resource_type", "article")),
                        description=resource_data.get("description"),
                        estimated_minutes=resource_data.get("estimated_minutes")
                    )
                    self.db.add(resource)
        
        self.db.commit()
        self.db.refresh(current_syllabus)
        
        logger.info(f"Updated syllabus {current_syllabus.id} for squad {squad_id}")
        
        return current_syllabus

        def update_syllabus_weekly(self, squad_id: UUID) -> Optional[Syllabus]:
            """
            Update syllabus based on weekly squad progress.

            Implements Requirement 3.5: Update syllabus at least once per week.

            This method checks if a week has passed since the last update and
            generates an updated syllabus based on squad progress and performance.

            Args:
                squad_id: Squad ID

            Returns:
                Updated Syllabus object or None if update not needed

            Raises:
                ValueError: If squad or syllabus not found
            """
            squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
            if not squad:
                raise ValueError(f"Squad {squad_id} not found")

            if not squad.current_syllabus_id:
                logger.warning(f"Squad {squad_id} has no active syllabus")
                return None

            # Get current syllabus
            current_syllabus = self.db.query(Syllabus).filter(
                Syllabus.id == squad.current_syllabus_id
            ).first()

            if not current_syllabus:
                raise ValueError(f"Current syllabus {squad.current_syllabus_id} not found")

            # Check if update is needed (7 days since last update)
            last_update = current_syllabus.last_updated_at or current_syllabus.created_at
            days_since_update = (datetime.utcnow() - last_update).days

            if days_since_update < 7:
                logger.info(f"Syllabus for squad {squad_id} was updated {days_since_update} days ago. No update needed.")
                return None

            # Get squad progress metrics
            completed_days = self.db.query(SyllabusDay).filter(
                SyllabusDay.syllabus_id == current_syllabus.id,
                SyllabusDay.completion_count >= squad.member_count * 0.5
            ).count()

            completion_rate = completed_days / squad.current_day if squad.current_day > 0 else 0

            # Check if pivot is needed instead
            if self.check_pivot_needed(squad_id):
                logger.info(f"Squad {squad_id} needs pivot instead of weekly update")
                return self.pivot_syllabus(
                    squad_id=squad_id,
                    reason="Low completion rate detected during weekly update"
                )

            # Get guild for context
            guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()

            # Build update prompt
            prompt = f"""Review and update the learning syllabus for a squad in the "{guild.name}" guild.

    Current Progress:
    - Days Completed: {completed_days}/{squad.current_day}
    - Completion Rate: {completion_rate:.1%}
    - Current Difficulty: {current_syllabus.difficulty_level}/10

    Analyze the squad's progress and make adjustments to the remaining days (day {squad.current_day + 1} to day 30):
    1. Reinforce concepts where completion is low
    2. Add supplementary resources for struggling topics
    3. Adjust pacing if squad is ahead or behind schedule
    4. Ensure project milestones are appropriately challenging

    Return a JSON object with the updated syllabus structure for the remaining days."""

            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an expert curriculum designer reviewing and updating learning paths."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )

                update_data = json.loads(response.choices[0].message.content)

            except Exception as e:
                logger.error(f"Error updating syllabus: {str(e)}")
                raise ValueError(f"Failed to update syllabus: {str(e)}")

            # Update the syllabus timestamp
            current_syllabus.last_updated_at = datetime.utcnow()

            # Update remaining days with new content
            for day_data in update_data.get("days", []):
                day_number = day_data.get("day_number")
                if day_number <= squad.current_day:
                    continue  # Skip already completed days

                # Find existing day
                existing_day = self.db.query(SyllabusDay).filter(
                    SyllabusDay.syllabus_id == current_syllabus.id,
                    SyllabusDay.day_number == day_number
                ).first()

                if existing_day:
                    # Update day content
                    existing_day.title = day_data.get("title", existing_day.title)
                    existing_day.learning_objectives = day_data.get("learning_objectives", existing_day.learning_objectives)

                    # Delete old tasks and resources
                    self.db.query(Task).filter(Task.syllabus_day_id == existing_day.id).delete()
                    self.db.query(Resource).filter(Resource.syllabus_day_id == existing_day.id).delete()

                    # Create new tasks
                    for task_data in day_data.get("tasks", []):
                        task = Task(
                            syllabus_day_id=existing_day.id,
                            title=task_data.get("title", "Untitled Task"),
                            description=task_data.get("description", ""),
                            task_type=TaskType(task_data.get("task_type", "reading")),
                            estimated_minutes=task_data.get("estimated_minutes", 60),
                            required=task_data.get("required", True),
                            order_index=task_data.get("order_index", 0)
                        )
                        self.db.add(task)

                    # Create new resources
                    for resource_data in day_data.get("resources", []):
                        resource = Resource(
                            syllabus_day_id=existing_day.id,
                            title=resource_data.get("title", "Untitled Resource"),
                            url=resource_data.get("url", ""),
                            resource_type=ResourceType(resource_data.get("resource_type", "article")),
                            description=resource_data.get("description"),
                            estimated_minutes=resource_data.get("estimated_minutes")
                        )
                        self.db.add(resource)

            self.db.commit()
            self.db.refresh(current_syllabus)

            logger.info(f"Updated syllabus {current_syllabus.id} for squad {squad_id}")

            return current_syllabus

        def generate_audio_standup(self, squad_id: UUID) -> Dict[str, Any]:
            """
            Generate weekly audio summary of squad progress.

            Implements Requirements:
            - 5.1: Generate audio standup every 7 days
            - 5.2: Include completion rates, top contributors, milestones
            - 5.4: Generate in user's preferred language

            Args:
                squad_id: Squad ID

            Returns:
                Dictionary with audio_url, transcript, and metadata

            Raises:
                ValueError: If squad not found or OpenAI not configured
            """
            squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
            if not squad:
                raise ValueError(f"Squad {squad_id} not found")

            if not squad.current_syllabus_id:
                raise ValueError(f"Squad {squad_id} has no active syllabus")

            # Get guild
            guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()

            # Get syllabus
            syllabus = self.db.query(Syllabus).filter(
                Syllabus.id == squad.current_syllabus_id
            ).first()

            # Calculate squad completion rate
            completed_days = self.db.query(SyllabusDay).filter(
                SyllabusDay.syllabus_id == syllabus.id,
                SyllabusDay.completion_count >= squad.member_count * 0.5
            ).count()

            completion_rate = (completed_days / squad.current_day * 100) if squad.current_day > 0 else 0

            # Get top contributors (users with most task completions)
            from app.models.syllabus import TaskCompletion
            from sqlalchemy import func

            top_contributors = self.db.query(
                User.id,
                User.profile,
                func.count(TaskCompletion.id).label('completion_count')
            ).join(
                TaskCompletion, TaskCompletion.user_id == User.id
            ).filter(
                TaskCompletion.squad_id == squad_id
            ).group_by(
                User.id, User.profile
            ).order_by(
                func.count(TaskCompletion.id).desc()
            ).limit(3).all()

            # Get upcoming milestones (next 7 days)
            upcoming_days = self.db.query(SyllabusDay).filter(
                SyllabusDay.syllabus_id == syllabus.id,
                SyllabusDay.day_number > squad.current_day,
                SyllabusDay.day_number <= squad.current_day + 7
            ).order_by(SyllabusDay.day_number).all()

            # Determine primary language (most common among squad members)
            from collections import Counter
            languages = []
            for membership in squad.memberships:
                user = self.db.query(User).filter(User.id == membership.user_id).first()
                if user and user.profile:
                    languages.append(user.profile.preferred_language)

            primary_language = Counter(languages).most_common(1)[0][0] if languages else "en"

            # Build standup script
            top_contributor_names = [
                user.profile.display_name if user.profile else f"User {user.id}"
                for user, profile, count in top_contributors
            ]

            milestone_summaries = [
                f"Day {day.day_number}: {day.title}"
                for day in upcoming_days
            ]

            script = f"""Weekly Squad Standup for {guild.name}

    Squad Progress Update:
    Your squad has completed {completed_days} out of {squad.current_day} days, achieving a {completion_rate:.1f}% completion rate.

    Top Contributors:
    {', '.join(top_contributor_names[:3]) if top_contributor_names else 'Keep pushing forward, everyone!'}

    Upcoming This Week:
    {chr(10).join(milestone_summaries) if milestone_summaries else 'Continue with your current learning path.'}

    Keep up the great work! Remember, learning together makes us stronger."""

            if not self.client:
                raise ValueError("OpenAI API key not configured")

            # Generate audio using OpenAI TTS
            try:
                # Map language codes to OpenAI voice models
                voice_map = {
                    "en": "alloy",
                    "es": "nova",
                    "fr": "shimmer",
                    "de": "echo",
                    "pt": "fable",
                    "zh": "onyx"
                }
                voice = voice_map.get(primary_language, "alloy")

                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=script
                )

                # Save audio file (in production, upload to S3/GCS)
                import os
                from datetime import datetime

                audio_dir = "audio_standups"
                os.makedirs(audio_dir, exist_ok=True)

                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"standup_{squad_id}_{timestamp}.mp3"
                filepath = os.path.join(audio_dir, filename)

                response.stream_to_file(filepath)

                audio_url = f"/audio/{filename}"  # In production, use CDN URL

                logger.info(f"Generated audio standup for squad {squad_id}: {audio_url}")

                return {
                    "audio_url": audio_url,
                    "transcript": script,
                    "language": primary_language,
                    "duration_seconds": len(script) // 15,  # Rough estimate
                    "generated_at": datetime.utcnow().isoformat(),
                    "squad_id": str(squad_id),
                    "completion_rate": completion_rate,
                    "top_contributors": top_contributor_names
                }

            except Exception as e:
                logger.error(f"Error generating audio standup: {str(e)}")
                raise ValueError(f"Failed to generate audio standup: {str(e)}")



    def generate_audio_standup(self, squad_id: UUID) -> Dict[str, Any]:
        """
        Generate weekly audio summary of squad progress.
        
        Implements Requirements:
        - 5.1: Generate audio standup every 7 days
        - 5.2: Include completion rates, top contributors, milestones
        - 5.4: Generate in user's preferred language
        
        Args:
            squad_id: Squad ID
            
        Returns:
            Dictionary with audio_url, transcript, and metadata
            
        Raises:
            ValueError: If squad not found or OpenAI not configured
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        if not squad.current_syllabus_id:
            raise ValueError(f"Squad {squad_id} has no active syllabus")
        
        # Get guild
        guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()
        
        # Get syllabus
        syllabus = self.db.query(Syllabus).filter(
            Syllabus.id == squad.current_syllabus_id
        ).first()
        
        # Calculate squad completion rate
        completed_days = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == syllabus.id,
            SyllabusDay.completion_count >= squad.member_count * 0.5
        ).count()
        
        completion_rate = (completed_days / squad.current_day * 100) if squad.current_day > 0 else 0
        
        # Get top contributors (users with most task completions)
        from app.models.syllabus import TaskCompletion
        from sqlalchemy import func
        
        top_contributors = self.db.query(
            User.id,
            User.profile,
            func.count(TaskCompletion.id).label('completion_count')
        ).join(
            TaskCompletion, TaskCompletion.user_id == User.id
        ).filter(
            TaskCompletion.squad_id == squad_id
        ).group_by(
            User.id, User.profile
        ).order_by(
            func.count(TaskCompletion.id).desc()
        ).limit(3).all()
        
        # Get upcoming milestones (next 7 days)
        upcoming_days = self.db.query(SyllabusDay).filter(
            SyllabusDay.syllabus_id == syllabus.id,
            SyllabusDay.day_number > squad.current_day,
            SyllabusDay.day_number <= squad.current_day + 7
        ).order_by(SyllabusDay.day_number).all()
        
        # Determine primary language (most common among squad members)
        from collections import Counter
        languages = []
        for membership in squad.memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if user and user.profile:
                languages.append(user.profile.preferred_language)
        
        primary_language = Counter(languages).most_common(1)[0][0] if languages else "en"
        
        # Build standup script
        top_contributor_names = [
            user.profile.display_name if user.profile else f"User {user.id}"
            for user, profile, count in top_contributors
        ]
        
        milestone_summaries = [
            f"Day {day.day_number}: {day.title}"
            for day in upcoming_days
        ]
        
        script = f"""Weekly Squad Standup for {guild.name}

Squad Progress Update:
Your squad has completed {completed_days} out of {squad.current_day} days, achieving a {completion_rate:.1f}% completion rate.

Top Contributors:
{', '.join(top_contributor_names[:3]) if top_contributor_names else 'Keep pushing forward, everyone!'}

Upcoming This Week:
{chr(10).join(milestone_summaries) if milestone_summaries else 'Continue with your current learning path.'}

Keep up the great work! Remember, learning together makes us stronger."""
        
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Generate audio using OpenAI TTS
        try:
            # Map language codes to OpenAI voice models
            voice_map = {
                "en": "alloy",
                "es": "nova",
                "fr": "shimmer",
                "de": "echo",
                "pt": "fable",
                "zh": "onyx"
            }
            voice = voice_map.get(primary_language, "alloy")
            
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=script
            )
            
            # Save audio file (in production, upload to S3/GCS)
            import os
            
            audio_dir = "audio_standups"
            os.makedirs(audio_dir, exist_ok=True)
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"standup_{squad_id}_{timestamp}.mp3"
            filepath = os.path.join(audio_dir, filename)
            
            response.stream_to_file(filepath)
            
            audio_url = f"/audio/{filename}"  # In production, use CDN URL
            
            logger.info(f"Generated audio standup for squad {squad_id}: {audio_url}")
            
            return {
                "audio_url": audio_url,
                "transcript": script,
                "language": primary_language,
                "duration_seconds": len(script) // 15,  # Rough estimate
                "generated_at": datetime.utcnow().isoformat(),
                "squad_id": str(squad_id),
                "completion_rate": completion_rate,
                "top_contributors": top_contributor_names
            }
            
        except Exception as e:
            logger.error(f"Error generating audio standup: {str(e)}")
            raise ValueError(f"Failed to generate audio standup: {str(e)}")

    def generate_icebreakers(self, squad_id: UUID) -> List[Dict[str, Any]]:
        """
        Generate personalized icebreaker questions for squad members.
        
        Implements Requirement 6.1: Generate icebreakers for new squads.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            List of icebreaker questions with target members
            
        Raises:
            ValueError: If squad not found or OpenAI not configured
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Get guild
        guild = self.db.query(Guild).filter(Guild.id == squad.guild_id).first()
        
        # Get squad members with profiles
        members = []
        for membership in squad.memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if user and user.profile:
                members.append({
                    "id": str(user.id),
                    "name": user.profile.display_name,
                    "skill_level": user.profile.skill_level,
                    "interest_area": user.profile.interest_area,
                    "timezone": user.profile.timezone,
                    "language": user.profile.preferred_language
                })
        
        if not members:
            raise ValueError(f"Squad {squad_id} has no members with profiles")
        
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Build prompt for icebreaker generation
        member_summaries = "\n".join([
            f"- {m['name']}: Skill level {m['skill_level']}/10, interested in {m['interest_area']}"
            for m in members
        ])
        
        prompt = f"""Generate personalized icebreaker questions for a new learning squad in the "{guild.name}" guild.

Squad Members:
{member_summaries}

Create 5-7 icebreaker questions that:
1. Help members discover shared interests or complementary skills
2. Are specific to the {guild.interest_area} domain
3. Encourage meaningful conversation
4. Are fun and engaging
5. Help build squad cohesion

Return a JSON array of icebreaker objects with this structure:
{{
  "icebreakers": [
    {{
      "question": "The icebreaker question",
      "purpose": "Why this question helps the squad connect",
      "target_members": ["member_name1", "member_name2"] or "all"
    }}
  ]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert facilitator creating engaging icebreaker questions for learning communities."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            
            icebreaker_data = json.loads(response.choices[0].message.content)
            icebreakers = icebreaker_data.get("icebreakers", [])
            
            logger.info(f"Generated {len(icebreakers)} icebreakers for squad {squad_id}")
            
            return icebreakers
            
        except Exception as e:
            logger.error(f"Error generating icebreakers: {str(e)}")
            raise ValueError(f"Failed to generate icebreakers: {str(e)}")

    def facilitate_networking(self, squad_id: UUID) -> List[Dict[str, Any]]:
        """
        Create 1-on-1 pairings for networking activity.
        
        Implements Requirement 6.3: Week-one networking activity.
        
        Args:
            squad_id: Squad ID
            
        Returns:
            List of member pairings for 1-on-1 introductions
            
        Raises:
            ValueError: If squad not found
        """
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Get squad members
        members = []
        for membership in squad.memberships:
            user = self.db.query(User).filter(User.id == membership.user_id).first()
            if user and user.profile:
                members.append({
                    "id": str(user.id),
                    "name": user.profile.display_name,
                    "timezone": user.profile.timezone
                })
        
        if len(members) < 2:
            raise ValueError(f"Squad {squad_id} needs at least 2 members for networking")
        
        # Create pairings using round-robin approach
        # This ensures everyone gets paired with someone different each time
        import random
        random.shuffle(members)
        
        pairings = []
        for i in range(0, len(members) - 1, 2):
            pairings.append({
                "member1": members[i],
                "member2": members[i + 1],
                "suggested_topics": [
                    "Share your learning goals for this squad",
                    "Discuss your favorite project you've worked on",
                    "Talk about what brought you to this guild"
                ]
            })
        
        # If odd number of members, create a trio with the last three
        if len(members) % 2 == 1:
            if len(pairings) > 0:
                # Add the last member to the last pairing to make a trio
                pairings[-1]["member3"] = members[-1]
            else:
                # Only one member, can't pair
                logger.warning(f"Squad {squad_id} has only 1 member, cannot create pairings")
        
        logger.info(f"Created {len(pairings)} networking pairings for squad {squad_id}")
        
        return pairings

    def assess_project(
        self,
        project_url: str,
        project_description: str,
        user_level: int,
        target_level: int,
        guild_interest_area: str
    ) -> Dict[str, Any]:
        """
        AI assessment of level-up project submission.
        
        Implements Requirement 8.2: AI assessment for all submissions.
        
        Args:
            project_url: URL to project (GitHub repo, portfolio, etc.)
            project_description: User's description of the project
            user_level: Current user level
            target_level: Target level for level-up
            guild_interest_area: Guild's interest area
            
        Returns:
            Dictionary with approved (bool), feedback (str), and scores
            
        Raises:
            ValueError: If OpenAI not configured
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Build assessment prompt
        prompt = f"""Assess a level-up project submission for a learning platform.

Project Details:
- URL: {project_url}
- Description: {project_description}
- Current Level: {user_level}/10
- Target Level: {target_level}/10
- Interest Area: {guild_interest_area}

Evaluation Criteria:
1. Technical Complexity: Does it demonstrate skills appropriate for level {target_level}?
2. Code Quality: Is the code well-structured, documented, and following best practices?
3. Completeness: Is the project fully functional and complete?
4. Innovation: Does it show creative problem-solving or unique approaches?
5. Relevance: Is it relevant to the {guild_interest_area} domain?

Provide a detailed assessment with:
- Overall approval decision (approve/reject)
- Scores for each criterion (1-10)
- Specific strengths
- Areas for improvement
- Actionable feedback for resubmission if rejected

Return JSON with this structure:
{{
  "approved": true/false,
  "overall_score": 7.5,
  "criteria_scores": {{
    "technical_complexity": 8,
    "code_quality": 7,
    "completeness": 8,
    "innovation": 7,
    "relevance": 8
  }},
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1", "improvement2"],
  "feedback": "Detailed feedback text",
  "recommendation": "approve/reject with reason"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert technical assessor evaluating project submissions for skill mastery verification."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for more consistent assessments
            )
            
            assessment = json.loads(response.choices[0].message.content)
            
            logger.info(f"Assessed project {project_url}: {'Approved' if assessment.get('approved') else 'Rejected'}")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error assessing project: {str(e)}")
            raise ValueError(f"Failed to assess project: {str(e)}")
