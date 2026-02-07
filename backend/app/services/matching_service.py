"""
Node Logic Matching Service

Implements squad formation and matching logic using vector similarity.

Implements Requirements:
- 2.2: Interest area filtering for squad matching
- 2.3: Cosine similarity calculation for compatibility
- 2.4: Similarity threshold enforcement (> 0.7)
- 2.5: Squad activation at threshold (12 members)
- 2.6: Squad size constraints (12-15 members)
- 2.7: Waiting pool management
"""
import logging
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import User, UserProfile
from app.models.guild import Guild, GuildMembership
from app.models.squad import Squad, SquadMembership, SquadStatus
from app.models.skill_assessment import VectorEmbedding
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)


class MatchingService:
    """Service for squad matching and formation using Node Logic algorithm."""
    
    # Squad formation constants
    MIN_SQUAD_SIZE = 12
    MAX_SQUAD_SIZE = 15
    MIN_SIMILARITY_THRESHOLD = 0.7
    TIMEZONE_TOLERANCE_HOURS = 3.0
    
    def __init__(self, db: Session):
        """
        Initialize matching service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.pinecone_service = PineconeService(db)
        logger.info("MatchingService initialized")
    
    def find_squad_matches(
        self,
        user_id: UUID,
        guild_id: UUID,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find compatible squads for a user within a specified guild.
        
        Implements Requirements:
        - 2.2: Filter by guild interest area
        - 2.3: Calculate cosine similarity
        - 2.4: Enforce similarity threshold > 0.7
        
        Args:
            user_id: User ID to find matches for
            guild_id: Guild ID to search within
            top_k: Maximum number of similar users to consider
            
        Returns:
            List of compatible squads with match scores and availability.
            Each item contains:
            - squad_id: Squad UUID
            - squad_name: Squad name
            - member_count: Current number of members
            - average_similarity: Average similarity with squad members
            - status: Squad status (FORMING or ACTIVE)
            - available_slots: Number of available slots
            
        Raises:
            ValueError: If user or guild not found
        """
        # Verify user exists and has profile
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            raise ValueError(f"User {user_id} not found or has no profile")
        
        # Verify guild exists
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        # Get user's profile for interest area
        user_profile = user.profile
        
        # Find similar users using Pinecone
        similar_users = self.pinecone_service.query_similar_users(
            user_id=user_id,
            guild_interest_area=guild.interest_area,
            top_k=top_k,
            min_similarity=self.MIN_SIMILARITY_THRESHOLD,
            timezone_tolerance_hours=self.TIMEZONE_TOLERANCE_HOURS,
            language=user_profile.preferred_language
        )
        
        if not similar_users:
            logger.info(f"No similar users found for user {user_id} in guild {guild_id}")
            return []
        
        # Get squads in this guild that have space
        available_squads = self.db.query(Squad).filter(
            and_(
                Squad.guild_id == guild_id,
                Squad.member_count < self.MAX_SQUAD_SIZE,
                or_(
                    Squad.status == SquadStatus.FORMING,
                    Squad.status == SquadStatus.ACTIVE
                )
            )
        ).all()
        
        if not available_squads:
            logger.info(f"No available squads in guild {guild_id}")
            return []
        
        # Calculate compatibility with each squad
        squad_matches = []
        
        for squad in available_squads:
            # Get squad member IDs
            squad_member_ids = [
                str(membership.user_id) 
                for membership in squad.memberships
            ]
            
            # Calculate average similarity with squad members
            similarities = []
            for similar_user in similar_users:
                if similar_user["user_id"] in squad_member_ids:
                    similarities.append(similar_user["similarity_score"])
            
            # Only include squad if we have similarity scores with members
            if similarities:
                average_similarity = sum(similarities) / len(similarities)
                
                # Only include if average similarity meets threshold
                if average_similarity >= self.MIN_SIMILARITY_THRESHOLD:
                    squad_matches.append({
                        "squad_id": str(squad.id),
                        "squad_name": squad.name,
                        "member_count": squad.member_count,
                        "average_similarity": round(average_similarity, 4),
                        "status": squad.status.value,
                        "available_slots": self.MAX_SQUAD_SIZE - squad.member_count
                    })
        
        # Sort by average similarity (descending)
        squad_matches.sort(key=lambda x: x["average_similarity"], reverse=True)
        
        logger.info(
            f"Found {len(squad_matches)} compatible squads for user {user_id} "
            f"in guild {guild_id}"
        )
        
        return squad_matches
    
    def create_new_squad(
        self,
        guild_id: UUID,
        initial_members: List[UUID],
        squad_name: Optional[str] = None
    ) -> Squad:
        """
        Create a new squad with initial members.
        
        Implements Requirements:
        - 2.4: Enforce similarity threshold > 0.7
        - 2.5: Squad activation at threshold (12 members)
        - 2.6: Squad size constraints (12-15 members)
        
        Args:
            guild_id: Guild ID for the squad
            initial_members: List of user IDs to add as initial members
            squad_name: Optional custom squad name
            
        Returns:
            Created Squad object
            
        Raises:
            ValueError: If guild not found, invalid member count, or members not compatible
        """
        # Verify guild exists
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        # Validate member count
        member_count = len(initial_members)
        if member_count < self.MIN_SQUAD_SIZE:
            raise ValueError(
                f"Cannot create squad with {member_count} members. "
                f"Minimum is {self.MIN_SQUAD_SIZE}"
            )
        
        if member_count > self.MAX_SQUAD_SIZE:
            raise ValueError(
                f"Cannot create squad with {member_count} members. "
                f"Maximum is {self.MAX_SQUAD_SIZE}"
            )
        
        # Verify all members exist and have profiles
        members = []
        for user_id in initial_members:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.profile:
                raise ValueError(f"User {user_id} not found or has no profile")
            members.append(user)
        
        # Verify members are compatible (similarity > 0.7)
        self._verify_member_compatibility(initial_members)
        
        # Generate squad name if not provided
        if not squad_name:
            squad_count = self.db.query(Squad).filter(Squad.guild_id == guild_id).count()
            squad_name = f"{guild.name} Squad {squad_count + 1}"
        
        # Determine initial status based on member count
        # Requirement 2.5: Mark as active at 12 members
        if member_count >= self.MIN_SQUAD_SIZE:
            status = SquadStatus.ACTIVE
        else:
            status = SquadStatus.FORMING
        
        # Calculate average skill level
        skill_levels = [user.profile.skill_level for user in members]
        average_skill_level = sum(skill_levels) / len(skill_levels)
        
        # Create squad
        squad = Squad(
            guild_id=guild_id,
            name=squad_name,
            status=status,
            member_count=member_count,
            average_skill_level=average_skill_level,
            average_completion_rate=0.0
        )
        
        self.db.add(squad)
        self.db.flush()  # Get squad ID
        
        # Create memberships
        for user_id in initial_members:
            membership = SquadMembership(
                user_id=user_id,
                squad_id=squad.id
            )
            self.db.add(membership)
        
        self.db.commit()
        self.db.refresh(squad)
        
        logger.info(
            f"Created squad {squad.id} ({squad.name}) in guild {guild_id} "
            f"with {member_count} members, status: {status.value}"
        )
        
        return squad

    
    def add_member_to_squad(
        self,
        squad_id: UUID,
        user_id: UUID
    ) -> Squad:
        """
        Add a user to an existing squad if compatible and space available.
        
        Implements Requirements:
        - 2.4: Enforce similarity threshold > 0.7
        - 2.5: Squad activation at threshold (12 members)
        - 2.6: Squad size constraints (12-15 members)
        
        Args:
            squad_id: Squad ID to add member to
            user_id: User ID to add
            
        Returns:
            Updated Squad object
            
        Raises:
            ValueError: If squad/user not found, squad full, or user not compatible
        """
        # Verify squad exists
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Check if squad has space
        if squad.member_count >= self.MAX_SQUAD_SIZE:
            raise ValueError(
                f"Squad {squad_id} is full ({squad.member_count}/{self.MAX_SQUAD_SIZE})"
            )
        
        # Verify user exists and has profile
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            raise ValueError(f"User {user_id} not found or has no profile")
        
        # Check if user is already in squad
        existing_membership = self.db.query(SquadMembership).filter(
            and_(
                SquadMembership.squad_id == squad_id,
                SquadMembership.user_id == user_id
            )
        ).first()
        
        if existing_membership:
            raise ValueError(f"User {user_id} is already in squad {squad_id}")
        
        # Get existing squad member IDs
        existing_member_ids = [
            membership.user_id 
            for membership in squad.memberships
        ]
        
        # Verify compatibility with existing members
        all_member_ids = existing_member_ids + [user_id]
        self._verify_member_compatibility(all_member_ids)
        
        # Add membership
        membership = SquadMembership(
            user_id=user_id,
            squad_id=squad_id
        )
        self.db.add(membership)
        
        # Update squad member count
        squad.member_count += 1
        
        # Update average skill level
        existing_members = self.db.query(User).filter(
            User.id.in_(existing_member_ids)
        ).all()
        
        skill_levels = [u.profile.skill_level for u in existing_members]
        skill_levels.append(user.profile.skill_level)
        squad.average_skill_level = sum(skill_levels) / len(skill_levels)
        
        # Requirement 2.5: Activate squad when it reaches 12 members
        if squad.member_count >= self.MIN_SQUAD_SIZE and squad.status == SquadStatus.FORMING:
            squad.status = SquadStatus.ACTIVE
            logger.info(f"Squad {squad_id} activated with {squad.member_count} members")
        
        self.db.commit()
        self.db.refresh(squad)
        
        logger.info(
            f"Added user {user_id} to squad {squad_id}. "
            f"New member count: {squad.member_count}/{self.MAX_SQUAD_SIZE}"
        )
        
        return squad
    
    def get_waiting_pool(
        self,
        guild_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get users waiting for squad assignment in a guild.
        
        Implements Requirement 2.7: Waiting pool management.
        
        Returns users who are guild members but not in any squad.
        
        Args:
            guild_id: Guild ID
            
        Returns:
            List of users in waiting pool with their profiles
            
        Raises:
            ValueError: If guild not found
        """
        # Verify guild exists
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        # Get all guild members
        guild_memberships = self.db.query(GuildMembership).filter(
            GuildMembership.guild_id == guild_id
        ).all()
        
        guild_member_ids = [membership.user_id for membership in guild_memberships]
        
        # Get users who are in squads
        squad_memberships = self.db.query(SquadMembership).join(Squad).filter(
            and_(
                Squad.guild_id == guild_id,
                SquadMembership.user_id.in_(guild_member_ids)
            )
        ).all()
        
        squad_member_ids = {membership.user_id for membership in squad_memberships}
        
        # Users in waiting pool = guild members - squad members
        waiting_user_ids = [
            user_id for user_id in guild_member_ids 
            if user_id not in squad_member_ids
        ]
        
        # Get user details
        waiting_users = self.db.query(User).filter(
            User.id.in_(waiting_user_ids)
        ).all()
        
        # Build response
        waiting_pool = []
        for user in waiting_users:
            if user.profile:
                waiting_pool.append({
                    "user_id": str(user.id),
                    "display_name": user.profile.display_name,
                    "skill_level": user.profile.skill_level,
                    "interest_area": user.profile.interest_area,
                    "timezone": user.profile.timezone,
                    "language": user.profile.preferred_language,
                    "joined_guild_at": next(
                        (m.joined_at.isoformat() for m in guild_memberships if m.user_id == user.id),
                        None
                    )
                })
        
        logger.info(f"Found {len(waiting_pool)} users in waiting pool for guild {guild_id}")
        
        return waiting_pool
    
    def add_to_waiting_pool(
        self,
        user_id: UUID,
        guild_id: UUID
    ) -> bool:
        """
        Add a user to the waiting pool for a guild.
        
        This is done by creating a guild membership without a squad membership.
        
        Args:
            user_id: User ID
            guild_id: Guild ID
            
        Returns:
            True if added successfully
            
        Raises:
            ValueError: If user/guild not found or user already in guild
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.profile:
            raise ValueError(f"User {user_id} not found or has no profile")
        
        # Verify guild exists
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        # Check if user is already in guild
        existing_membership = self.db.query(GuildMembership).filter(
            and_(
                GuildMembership.user_id == user_id,
                GuildMembership.guild_id == guild_id
            )
        ).first()
        
        if existing_membership:
            logger.info(f"User {user_id} is already in guild {guild_id}")
            return True
        
        # Create guild membership
        membership = GuildMembership(
            user_id=user_id,
            guild_id=guild_id
        )
        self.db.add(membership)
        self.db.commit()
        
        logger.info(f"Added user {user_id} to waiting pool for guild {guild_id}")
        
        return True
    
    def _verify_member_compatibility(
        self,
        member_ids: List[UUID]
    ) -> bool:
        """
        Verify that all members are compatible with each other.
        
        Implements Requirement 2.4: Enforce similarity threshold > 0.7.
        
        Checks pairwise similarity between all members to ensure they meet
        the minimum similarity threshold.
        
        Args:
            member_ids: List of user IDs to check
            
        Returns:
            True if all members are compatible
            
        Raises:
            ValueError: If any pair of members has similarity < 0.7
        """
        if len(member_ids) < 2:
            return True
        
        # Check pairwise similarity
        incompatible_pairs = []
        
        for i in range(len(member_ids)):
            for j in range(i + 1, len(member_ids)):
                user_id_1 = member_ids[i]
                user_id_2 = member_ids[j]
                
                try:
                    similarity = self.pinecone_service.calculate_similarity(
                        user_id_1, user_id_2
                    )
                    
                    if similarity < self.MIN_SIMILARITY_THRESHOLD:
                        incompatible_pairs.append({
                            "user_1": str(user_id_1),
                            "user_2": str(user_id_2),
                            "similarity": round(similarity, 4)
                        })
                
                except Exception as e:
                    logger.error(
                        f"Error calculating similarity between {user_id_1} and {user_id_2}: {str(e)}"
                    )
                    raise ValueError(
                        f"Cannot verify compatibility: {str(e)}"
                    )
        
        if incompatible_pairs:
            raise ValueError(
                f"Members are not compatible. Found {len(incompatible_pairs)} pairs "
                f"with similarity < {self.MIN_SIMILARITY_THRESHOLD}: {incompatible_pairs}"
            )
        
        logger.debug(f"Verified compatibility for {len(member_ids)} members")
        return True
    
    def calculate_compatibility(
        self,
        user_id_1: UUID,
        user_id_2: UUID
    ) -> float:
        """
        Calculate cosine similarity between two users' embeddings.
        
        Implements Requirement 2.3: Compute cosine similarity between user embeddings.
        
        Args:
            user_id_1: First user ID
            user_id_2: Second user ID
            
        Returns:
            Cosine similarity score between -1 and 1
            
        Raises:
            ValueError: If either user's embedding is not found
        """
        return self.pinecone_service.calculate_similarity(user_id_1, user_id_2)

    
    def notify_waiting_pool_matches(
        self,
        guild_id: UUID
    ) -> Dict[str, Any]:
        """
        Check waiting pool and notify users when enough compatible members are available.
        
        Implements Requirement 2.7: Notify when matches become available.
        
        This method checks if there are enough compatible users in the waiting pool
        to form a new squad (12+ members with similarity > 0.7). If so, it identifies
        the compatible group and triggers notifications.
        
        Args:
            guild_id: Guild ID to check
            
        Returns:
            Dictionary containing:
            - compatible_groups: List of groups that can form squads
            - notifications_sent: Number of notifications sent
            - users_notified: List of user IDs notified
            
        Raises:
            ValueError: If guild not found
        """
        # Verify guild exists
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        # Get waiting pool
        waiting_pool = self.get_waiting_pool(guild_id)
        
        if len(waiting_pool) < self.MIN_SQUAD_SIZE:
            logger.info(
                f"Waiting pool for guild {guild_id} has {len(waiting_pool)} users. "
                f"Need {self.MIN_SQUAD_SIZE} to form squad."
            )
            return {
                "compatible_groups": [],
                "notifications_sent": 0,
                "users_notified": []
            }
        
        # Extract user IDs from waiting pool
        waiting_user_ids = [UUID(user["user_id"]) for user in waiting_pool]
        
        # Find compatible groups using clustering approach
        compatible_groups = self._find_compatible_groups(
            waiting_user_ids,
            guild.interest_area
        )
        
        # Notify users in compatible groups
        users_notified = []
        notifications_sent = 0
        
        for group in compatible_groups:
            for user_id in group["members"]:
                # TODO: Integrate with NotificationService when implemented (Task 14)
                # For now, log the notification
                logger.info(
                    f"NOTIFICATION: User {user_id} - Squad match available in guild {guild_id}. "
                    f"Compatible group of {len(group['members'])} members found."
                )
                users_notified.append(str(user_id))
                notifications_sent += 1
        
        logger.info(
            f"Found {len(compatible_groups)} compatible groups in waiting pool for guild {guild_id}. "
            f"Sent {notifications_sent} notifications."
        )
        
        return {
            "compatible_groups": [
                {
                    "member_count": len(group["members"]),
                    "average_similarity": group["average_similarity"],
                    "members": [str(uid) for uid in group["members"]]
                }
                for group in compatible_groups
            ],
            "notifications_sent": notifications_sent,
            "users_notified": users_notified
        }
    
    def _find_compatible_groups(
        self,
        user_ids: List[UUID],
        interest_area: str
    ) -> List[Dict[str, Any]]:
        """
        Find compatible groups of users that can form squads.
        
        Uses a greedy clustering approach to find groups of 12-15 users
        where all members have pairwise similarity > 0.7.
        
        Args:
            user_ids: List of user IDs to group
            interest_area: Interest area for filtering
            
        Returns:
            List of compatible groups, each containing:
            - members: List of user IDs
            - average_similarity: Average pairwise similarity
        """
        if len(user_ids) < self.MIN_SQUAD_SIZE:
            return []
        
        compatible_groups = []
        remaining_users = set(user_ids)
        
        while len(remaining_users) >= self.MIN_SQUAD_SIZE:
            # Start with first remaining user
            seed_user = next(iter(remaining_users))
            
            # Find similar users using Pinecone
            try:
                similar_users = self.pinecone_service.query_similar_users(
                    user_id=seed_user,
                    guild_interest_area=interest_area,
                    top_k=self.MAX_SQUAD_SIZE,
                    min_similarity=self.MIN_SIMILARITY_THRESHOLD
                )
            except Exception as e:
                logger.error(f"Error querying similar users for {seed_user}: {str(e)}")
                remaining_users.remove(seed_user)
                continue
            
            # Filter to only users in remaining pool
            similar_user_ids = [
                UUID(user["user_id"]) 
                for user in similar_users 
                if UUID(user["user_id"]) in remaining_users
            ]
            
            # Build group starting with seed user
            group_members = [seed_user]
            
            # Add compatible users up to MAX_SQUAD_SIZE
            for candidate_id in similar_user_ids:
                if len(group_members) >= self.MAX_SQUAD_SIZE:
                    break
                
                # Check if candidate is compatible with all current group members
                is_compatible = True
                for member_id in group_members:
                    try:
                        similarity = self.pinecone_service.calculate_similarity(
                            candidate_id, member_id
                        )
                        if similarity < self.MIN_SIMILARITY_THRESHOLD:
                            is_compatible = False
                            break
                    except Exception as e:
                        logger.error(
                            f"Error calculating similarity between {candidate_id} and {member_id}: {str(e)}"
                        )
                        is_compatible = False
                        break
                
                if is_compatible:
                    group_members.append(candidate_id)
            
            # If we have enough members, this is a valid group
            if len(group_members) >= self.MIN_SQUAD_SIZE:
                # Calculate average pairwise similarity
                similarities = []
                for i in range(len(group_members)):
                    for j in range(i + 1, len(group_members)):
                        try:
                            sim = self.pinecone_service.calculate_similarity(
                                group_members[i], group_members[j]
                            )
                            similarities.append(sim)
                        except Exception:
                            pass
                
                avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
                
                compatible_groups.append({
                    "members": group_members,
                    "average_similarity": avg_similarity
                })
                
                # Remove group members from remaining pool
                for member_id in group_members:
                    remaining_users.discard(member_id)
            else:
                # Not enough compatible users, remove seed and try next
                remaining_users.remove(seed_user)
        
        return compatible_groups
    
    def auto_form_squads_from_waiting_pool(
        self,
        guild_id: UUID
    ) -> List[Squad]:
        """
        Automatically form squads from compatible groups in the waiting pool.
        
        This is a convenience method that finds compatible groups and creates
        squads for them automatically.
        
        Args:
            guild_id: Guild ID
            
        Returns:
            List of created Squad objects
            
        Raises:
            ValueError: If guild not found
        """
        # Find compatible groups
        result = self.notify_waiting_pool_matches(guild_id)
        
        if not result["compatible_groups"]:
            logger.info(f"No compatible groups found in waiting pool for guild {guild_id}")
            return []
        
        # Create squads for each compatible group
        created_squads = []
        
        for group in result["compatible_groups"]:
            member_ids = [UUID(uid) for uid in group["members"]]
            
            try:
                squad = self.create_new_squad(
                    guild_id=guild_id,
                    initial_members=member_ids
                )
                created_squads.append(squad)
                
                logger.info(
                    f"Auto-formed squad {squad.id} with {len(member_ids)} members "
                    f"from waiting pool in guild {guild_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create squad from waiting pool group: {str(e)}"
                )
        
        return created_squads
