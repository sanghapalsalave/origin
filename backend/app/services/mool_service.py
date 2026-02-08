"""
Mool Reputation System Service

Provides reputation management, peer review, and level-up verification functionality.

Implements Requirements:
- 7.1: Work submission for review
- 7.2: Peer review completion and reputation award
- 7.3: Reputation weighting by reviewer level
- 7.4: Reputation tracking and display
- 7.5: Reviewer privilege unlocking
- 7.6: Collaborator exclusion
- 8.1-8.6: Level-up project submission and assessment
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.mool import WorkSubmission, PeerReview, LevelUpRequest, ProjectAssessment, LevelUpStatus
from app.models.user import User
from app.models.squad import Squad, SquadMembership
from app.models.guild import Guild, GuildMembership

logger = logging.getLogger(__name__)


class MoolService:
    """Service for Mool reputation system operations."""
    
    def __init__(self, db: Session):
        """
        Initialize Mool service.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("MoolService initialized")
    
    def submit_work_for_review(
        self,
        user_id: UUID,
        squad_id: UUID,
        title: str,
        description: str,
        submission_url: str
    ) -> WorkSubmission:
        """
        Submit work for peer review.
        
        Creates a work submission and notifies eligible reviewers within the same guild.
        Eligible reviewers are guild members who are not direct collaborators on the
        same project (same squad).
        
        Implements Requirements:
        - 7.1: Work submission for review and notification
        - 7.6: Exclude direct collaborators
        
        Args:
            user_id: ID of user submitting work
            squad_id: ID of user's squad
            title: Submission title
            description: Detailed description of work
            submission_url: URL to work (GitHub repo, portfolio link, etc.)
            
        Returns:
            Created WorkSubmission object
            
        Raises:
            ValueError: If user, squad not found, or user not in squad
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate squad exists
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()
        if not squad:
            raise ValueError(f"Squad {squad_id} not found")
        
        # Verify user is member of squad
        membership = self.db.query(SquadMembership).filter(
            and_(
                SquadMembership.user_id == user_id,
                SquadMembership.squad_id == squad_id
            )
        ).first()
        
        if not membership:
            raise ValueError(f"User {user_id} is not a member of squad {squad_id}")
        
        # Create work submission
        submission = WorkSubmission(
            user_id=user_id,
            squad_id=squad_id,
            title=title,
            description=description,
            submission_url=submission_url,
            submitted_at=datetime.utcnow()
        )
        
        self.db.add(submission)
        self.db.flush()  # Flush to get submission ID
        
        # Get eligible reviewers and notify them
        eligible_reviewers = self.get_eligible_reviewers(submission)
        
        logger.info(
            f"Work submission {submission.id} created by user {user_id}. "
            f"Found {len(eligible_reviewers)} eligible reviewers."
        )
        
        # TODO: In a future task, integrate with notification service to send notifications
        # For now, we log the eligible reviewers
        for reviewer in eligible_reviewers:
            logger.info(f"Eligible reviewer: {reviewer.id} ({reviewer.email})")
        
        self.db.commit()
        self.db.refresh(submission)
        
        return submission
    
    def get_eligible_reviewers(self, work_submission: WorkSubmission) -> List[User]:
        """
        Find users eligible to review a work submission.
        
        Eligible reviewers are:
        1. Members of the same guild as the submitter
        2. NOT members of the same squad (direct collaborators excluded)
        
        Implements Requirements:
        - 7.1: Notify eligible reviewers within guild
        - 7.6: Exclude direct collaborators
        
        Args:
            work_submission: WorkSubmission object
            
        Returns:
            List of eligible User objects
        """
        # Get the squad and guild
        squad = self.db.query(Squad).filter(Squad.id == work_submission.squad_id).first()
        if not squad:
            logger.warning(f"Squad {work_submission.squad_id} not found")
            return []
        
        guild_id = squad.guild_id
        
        # Get all users in the same guild
        guild_member_ids = self.db.query(GuildMembership.user_id).filter(
            GuildMembership.guild_id == guild_id
        ).all()
        guild_member_ids = [uid[0] for uid in guild_member_ids]
        
        # Get all users in the same squad (direct collaborators to exclude)
        squad_member_ids = self.db.query(SquadMembership.user_id).filter(
            SquadMembership.squad_id == work_submission.squad_id
        ).all()
        squad_member_ids = [uid[0] for uid in squad_member_ids]
        
        # Find eligible reviewers: in guild but not in same squad
        eligible_user_ids = set(guild_member_ids) - set(squad_member_ids)
        
        # Exclude the submitter themselves (in case they're in multiple squads)
        eligible_user_ids.discard(work_submission.user_id)
        
        # Get User objects
        eligible_reviewers = self.db.query(User).filter(
            User.id.in_(eligible_user_ids)
        ).all()
        
        logger.info(
            f"Found {len(eligible_reviewers)} eligible reviewers for submission {work_submission.id} "
            f"(guild: {guild_id}, excluded squad: {work_submission.squad_id})"
        )
        
        return eligible_reviewers
    
    def calculate_reputation_award(
        self,
        review_content: str,
        reviewer_level: int,
        submission_time: datetime,
        review_time: datetime
    ) -> int:
        """
        Calculate reputation points for a peer review.
        
        Formula: base_points * (1 + reviewer_level * 0.1) + quality_bonus + consistency_bonus
        - Base points: 10
        - Level multiplier: 1 + (reviewer_level * 0.1)
        - Quality bonus: +5 for detailed reviews (> 200 words)
        - Consistency bonus: +3 for reviews within 24 hours
        - Maximum points: 25
        
        Implements Requirements:
        - 7.2: Reputation point calculation
        - 7.3: Weight reviews from higher-level users more heavily
        
        Args:
            review_content: Text content of the review
            reviewer_level: Level of the reviewer
            submission_time: When work was submitted
            review_time: When review was submitted
            
        Returns:
            Calculated reputation points (capped at 25)
        """
        base_points = 10
        
        # Level multiplier
        level_multiplier = 1 + (reviewer_level * 0.1)
        points = base_points * level_multiplier
        
        # Quality bonus: +5 for detailed reviews (> 200 words)
        word_count = len(review_content.split())
        if word_count > 200:
            points += 5
            logger.debug(f"Quality bonus applied: {word_count} words")
        
        # Consistency bonus: +3 for reviews within 24 hours
        time_diff = review_time - submission_time
        if time_diff <= timedelta(hours=24):
            points += 3
            logger.debug(f"Consistency bonus applied: reviewed in {time_diff}")
        
        # Cap at maximum 25 points
        points = min(int(points), 25)
        
        logger.info(
            f"Reputation calculated: {points} points "
            f"(base={base_points}, level={reviewer_level}, words={word_count}, "
            f"time_diff={time_diff})"
        )
        
        return points
    
    def submit_peer_review(
        self,
        reviewer_id: UUID,
        submission_id: UUID,
        review_content: str,
        rating: int
    ) -> PeerReview:
        """
        Submit a peer review and award reputation points to the reviewer.
        
        Calculates reputation points using the formula:
        base_points * (1 + reviewer_level * 0.1) + quality_bonus + consistency_bonus
        
        Then awards the calculated points to the reviewer by updating their
        reputation_points field.
        
        Implements Requirements:
        - 7.2: Peer review completion and reputation award
        - 7.3: Reputation weighting by reviewer level
        
        Args:
            reviewer_id: ID of user submitting the review
            submission_id: ID of work submission being reviewed
            review_content: Text content of the review
            rating: Rating on 1-5 scale
            
        Returns:
            Created PeerReview object
            
        Raises:
            ValueError: If reviewer, submission not found, or rating invalid
        """
        # Validate reviewer exists
        reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
        if not reviewer:
            raise ValueError(f"Reviewer {reviewer_id} not found")
        
        # Validate submission exists
        submission = self.db.query(WorkSubmission).filter(
            WorkSubmission.id == submission_id
        ).first()
        if not submission:
            raise ValueError(f"Work submission {submission_id} not found")
        
        # Validate rating
        if not (1 <= rating <= 5):
            raise ValueError(f"Rating must be between 1 and 5, got {rating}")
        
        # Calculate reputation points
        reputation_points = self.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer.current_level,
            submission_time=submission.submitted_at,
            review_time=datetime.utcnow()
        )
        
        # Create peer review
        review = PeerReview(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            review_content=review_content,
            rating=rating,
            reputation_awarded=reputation_points,
            submitted_at=datetime.utcnow()
        )
        
        self.db.add(review)
        
        # Award reputation points to reviewer
        reviewer.reputation_points += reputation_points
        
        logger.info(
            f"Peer review {review.id} submitted by reviewer {reviewer_id} "
            f"for submission {submission_id}. Awarded {reputation_points} reputation points. "
            f"Reviewer total reputation: {reviewer.reputation_points}"
        )
        
        self.db.commit()
        self.db.refresh(review)
        
        return review
    
    def get_user_reputation(self, user_id: UUID) -> int:
        """
        Get total reputation points for a user.
        
        Returns the user's current reputation_points field, which is maintained
        as a running total when peer reviews are submitted.
        
        Implements Requirement 7.4: Track and display reputation points.
        
        Args:
            user_id: User ID
            
        Returns:
            Total reputation points
            
        Raises:
            ValueError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        return user.reputation_points
    
    def calculate_user_reputation_from_reviews(self, user_id: UUID) -> int:
        """
        Calculate total reputation by aggregating all peer reviews.
        
        This method recalculates reputation from scratch by summing all
        reputation_awarded values from peer reviews. Useful for verification
        and audit purposes to ensure the running total is accurate.
        
        Implements Requirement 7.4: Track and display reputation points.
        
        Args:
            user_id: User ID
            
        Returns:
            Total reputation points calculated from all reviews
            
        Raises:
            ValueError: If user not found
        """
        from sqlalchemy import func
        
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Sum all reputation_awarded from peer reviews where user is the reviewer
        total_reputation = self.db.query(
            func.coalesce(func.sum(PeerReview.reputation_awarded), 0)
        ).filter(
            PeerReview.reviewer_id == user_id
        ).scalar()
        
        logger.info(
            f"Calculated reputation for user {user_id} from reviews: {total_reputation} "
            f"(stored value: {user.reputation_points})"
        )
        
        return int(total_reputation)
    
    def get_user_reputation_breakdown(self, user_id: UUID) -> dict:
        """
        Get detailed breakdown of user's reputation points.
        
        Provides information about:
        - Total reputation points
        - Number of reviews completed
        - Average reputation per review
        - Recent reviews (last 10)
        
        Implements Requirement 7.4: Track and display reputation points.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with reputation breakdown:
            {
                'total_reputation': int,
                'review_count': int,
                'average_per_review': float,
                'recent_reviews': List[dict]
            }
            
        Raises:
            ValueError: If user not found
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get all peer reviews by this user
        reviews = self.db.query(PeerReview).filter(
            PeerReview.reviewer_id == user_id
        ).order_by(PeerReview.submitted_at.desc()).all()
        
        review_count = len(reviews)
        total_reputation = sum(review.reputation_awarded for review in reviews)
        average_per_review = total_reputation / review_count if review_count > 0 else 0.0
        
        # Get recent reviews (last 10)
        recent_reviews = []
        for review in reviews[:10]:
            recent_reviews.append({
                'review_id': str(review.id),
                'submission_id': str(review.submission_id),
                'reputation_awarded': review.reputation_awarded,
                'rating': review.rating,
                'submitted_at': review.submitted_at.isoformat()
            })
        
        breakdown = {
            'total_reputation': total_reputation,
            'review_count': review_count,
            'average_per_review': round(average_per_review, 2),
            'recent_reviews': recent_reviews
        }
        
        logger.info(
            f"Reputation breakdown for user {user_id}: "
            f"{total_reputation} points from {review_count} reviews"
        )
        
        return breakdown
    
    def unlock_reviewer_privileges(self, user_id: UUID) -> dict:
        """
        Unlock reviewer privileges for higher-level submissions based on reputation.
        
        Users can review submissions from users at their own level or below by default.
        As users accumulate reputation points, they unlock the ability to review
        submissions from users at progressively higher levels.
        
        Reputation thresholds for unlocking review privileges:
        - 0 points: Can review submissions from users at own level or below
        - 50 points: Can review submissions from users 1 level above
        - 150 points: Can review submissions from users 2 levels above
        - 300 points: Can review submissions from users 3 levels above
        - 500 points: Can review submissions from users 4 levels above
        - 750 points: Can review submissions from users 5+ levels above
        
        Implements Requirement 7.5: Unlock reviewer privileges for higher-level submissions.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with privilege information:
            {
                'user_id': str,
                'current_level': int,
                'reputation_points': int,
                'max_reviewable_level': int,
                'levels_above_unlocked': int,
                'next_unlock_at': int or None,
                'next_unlock_levels': int or None
            }
            
        Raises:
            ValueError: If user not found
        """
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Define reputation thresholds for unlocking review privileges
        # Each threshold unlocks the ability to review submissions from users N levels above
        REPUTATION_THRESHOLDS = [
            (0, 0),      # 0 points: own level or below
            (50, 1),     # 50 points: +1 level above
            (150, 2),    # 150 points: +2 levels above
            (300, 3),    # 300 points: +3 levels above
            (500, 4),    # 500 points: +4 levels above
            (750, 5),    # 750 points: +5+ levels above
        ]
        
        reputation = user.reputation_points
        current_level = user.current_level
        
        # Determine current privilege level
        levels_above_unlocked = 0
        next_unlock_at = None
        next_unlock_levels = None
        
        for threshold, levels_above in REPUTATION_THRESHOLDS:
            if reputation >= threshold:
                levels_above_unlocked = levels_above
            else:
                # Found the next threshold to unlock
                next_unlock_at = threshold
                next_unlock_levels = levels_above
                break
        
        # Calculate maximum reviewable level
        max_reviewable_level = current_level + levels_above_unlocked
        
        result = {
            'user_id': str(user_id),
            'current_level': current_level,
            'reputation_points': reputation,
            'max_reviewable_level': max_reviewable_level,
            'levels_above_unlocked': levels_above_unlocked,
            'next_unlock_at': next_unlock_at,
            'next_unlock_levels': next_unlock_levels
        }
        
        logger.info(
            f"Reviewer privileges for user {user_id}: "
            f"Level {current_level}, {reputation} reputation points, "
            f"can review up to level {max_reviewable_level} "
            f"({levels_above_unlocked} levels above)"
        )
        
        return result
    
    def can_review_submission(self, reviewer_id: UUID, submission_id: UUID) -> tuple[bool, str]:
        """
        Check if a user can review a specific work submission.
        
        A user can review a submission if:
        1. They are not the submitter
        2. They are not in the same squad (direct collaborators excluded)
        3. The submitter's level is within their reviewable range based on reputation
        
        Implements Requirements:
        - 7.5: Reviewer privilege unlocking
        - 7.6: Collaborator exclusion
        
        Args:
            reviewer_id: ID of potential reviewer
            submission_id: ID of work submission
            
        Returns:
            Tuple of (can_review: bool, reason: str)
            - can_review: True if user can review, False otherwise
            - reason: Explanation of the decision
            
        Raises:
            ValueError: If reviewer or submission not found
        """
        # Verify reviewer exists
        reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
        if not reviewer:
            raise ValueError(f"Reviewer {reviewer_id} not found")
        
        # Verify submission exists
        submission = self.db.query(WorkSubmission).filter(
            WorkSubmission.id == submission_id
        ).first()
        if not submission:
            raise ValueError(f"Work submission {submission_id} not found")
        
        # Check 1: Cannot review own submission
        if submission.user_id == reviewer_id:
            return False, "Cannot review your own submission"
        
        # Check 2: Cannot review if in same squad (direct collaborators)
        reviewer_squad_ids = set(
            sm.squad_id for sm in 
            self.db.query(SquadMembership).filter(
                SquadMembership.user_id == reviewer_id
            ).all()
        )
        
        if submission.squad_id in reviewer_squad_ids:
            return False, "Cannot review submissions from squad members (direct collaborators)"
        
        # Check 3: Check if submitter's level is within reviewable range
        submitter = self.db.query(User).filter(User.id == submission.user_id).first()
        if not submitter:
            logger.warning(f"Submitter {submission.user_id} not found for submission {submission_id}")
            return False, "Submitter not found"
        
        privileges = self.unlock_reviewer_privileges(reviewer_id)
        max_reviewable_level = privileges['max_reviewable_level']
        
        if submitter.current_level > max_reviewable_level:
            return False, (
                f"Insufficient reputation to review level {submitter.current_level} submissions. "
                f"You can review up to level {max_reviewable_level}. "
                f"Earn more reputation points to unlock higher-level reviews."
            )
        
        # All checks passed
        return True, "Eligible to review this submission"
    
    def submit_levelup_project(
        self,
        user_id: UUID,
        project_title: str,
        project_description: str,
        project_url: str
    ) -> LevelUpRequest:
        """
        Submit a level-up project for assessment.
        
        Creates a level-up request when a user has completed all requirements
        for their current level. The project will undergo:
        1. AI Guild Master automated quality assessment
        2. Two peer reviews from senior guild members (2+ levels higher)
        3. Approval from both AI and both peer reviewers required
        
        Implements Requirements:
        - 8.1: Level-up project submission
        - 8.2: AI automated quality assessment (triggered)
        
        Args:
            user_id: ID of user submitting level-up project
            project_title: Title of the level-up project
            project_description: Detailed description of the project
            project_url: URL to project (GitHub repo, demo link, etc.)
            
        Returns:
            Created LevelUpRequest object
            
        Raises:
            ValueError: If user not found or has pending level-up request
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user already has a pending level-up request
        existing_request = self.db.query(LevelUpRequest).filter(
            and_(
                LevelUpRequest.user_id == user_id,
                LevelUpRequest.status.in_([
                    LevelUpStatus.PENDING,
                    LevelUpStatus.AI_APPROVED,
                    LevelUpStatus.PEER_REVIEW
                ])
            )
        ).first()
        
        if existing_request:
            raise ValueError(
                f"User {user_id} already has a pending level-up request "
                f"(ID: {existing_request.id}, status: {existing_request.status})"
            )
        
        # Create level-up request
        current_level = user.current_level
        target_level = current_level + 1
        
        levelup_request = LevelUpRequest(
            user_id=user_id,
            current_level=current_level,
            target_level=target_level,
            project_title=project_title,
            project_description=project_description,
            project_url=project_url,
            status=LevelUpStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        self.db.add(levelup_request)
        self.db.flush()
        
        logger.info(
            f"Level-up request {levelup_request.id} created by user {user_id} "
            f"(level {current_level} -> {target_level})"
        )
        
        # TODO: In a future task, trigger AI Guild Master assessment
        # For now, we just create the request
        
        self.db.commit()
        self.db.refresh(levelup_request)
        
        return levelup_request
    
    def get_levelup_request(self, request_id: UUID) -> Optional[LevelUpRequest]:
        """
        Get a level-up request by ID.
        
        Args:
            request_id: Level-up request ID
            
        Returns:
            LevelUpRequest object or None if not found
        """
        return self.db.query(LevelUpRequest).filter(
            LevelUpRequest.id == request_id
        ).first()
    
    def get_user_levelup_requests(self, user_id: UUID) -> List[LevelUpRequest]:
        """
        Get all level-up requests for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of LevelUpRequest objects ordered by creation date (newest first)
        """
        return self.db.query(LevelUpRequest).filter(
            LevelUpRequest.user_id == user_id
        ).order_by(LevelUpRequest.created_at.desc()).all()
    
    def assign_peer_reviewers(self, levelup_request_id: UUID) -> List[User]:
        """
        Assign exactly 2 peer reviewers to a level-up request.
        
        Peer reviewers must be:
        1. At least 2 levels higher than the submitting user's current level
        2. Members of the same guild as the submitter
        3. Not the submitter themselves
        
        Implements Requirements:
        - 8.3: Peer reviewer assignment count (exactly 2)
        - 8.6: Peer reviewer level requirement (2+ levels higher)
        
        Args:
            levelup_request_id: Level-up request ID
            
        Returns:
            List of 2 assigned User objects
            
        Raises:
            ValueError: If request not found, not enough eligible reviewers,
                       or reviewers already assigned
        """
        # Get level-up request
        levelup_request = self.db.query(LevelUpRequest).filter(
            LevelUpRequest.id == levelup_request_id
        ).first()
        
        if not levelup_request:
            raise ValueError(f"Level-up request {levelup_request_id} not found")
        
        # Check if reviewers already assigned
        existing_peer_assessments = self.db.query(ProjectAssessment).filter(
            and_(
                ProjectAssessment.levelup_request_id == levelup_request_id,
                ProjectAssessment.assessment_type == "peer"
            )
        ).count()
        
        if existing_peer_assessments > 0:
            raise ValueError(
                f"Peer reviewers already assigned to level-up request {levelup_request_id}"
            )
        
        # Get submitter
        submitter = self.db.query(User).filter(
            User.id == levelup_request.user_id
        ).first()
        
        if not submitter:
            raise ValueError(f"Submitter {levelup_request.user_id} not found")
        
        # Find submitter's guild(s)
        submitter_guild_ids = [
            gm.guild_id for gm in 
            self.db.query(GuildMembership).filter(
                GuildMembership.user_id == submitter.id
            ).all()
        ]
        
        if not submitter_guild_ids:
            raise ValueError(f"Submitter {submitter.id} is not a member of any guild")
        
        # Find eligible reviewers: guild members who are 2+ levels higher
        minimum_reviewer_level = levelup_request.current_level + 2
        
        eligible_reviewers = self.db.query(User).join(
            GuildMembership,
            GuildMembership.user_id == User.id
        ).filter(
            and_(
                GuildMembership.guild_id.in_(submitter_guild_ids),
                User.current_level >= minimum_reviewer_level,
                User.id != submitter.id
            )
        ).distinct().all()
        
        if len(eligible_reviewers) < 2:
            raise ValueError(
                f"Not enough eligible reviewers for level-up request {levelup_request_id}. "
                f"Need 2 reviewers at level {minimum_reviewer_level}+, found {len(eligible_reviewers)}"
            )
        
        # Select 2 reviewers (for now, just take first 2; could be randomized or based on availability)
        assigned_reviewers = eligible_reviewers[:2]
        
        logger.info(
            f"Assigned {len(assigned_reviewers)} peer reviewers to level-up request {levelup_request_id}: "
            f"{[str(r.id) for r in assigned_reviewers]}"
        )
        
        # TODO: In a future task, create ProjectAssessment records and send notifications
        # For now, we just return the assigned reviewers
        
        return assigned_reviewers
    
    def process_levelup_approval(self, levelup_request_id: UUID) -> dict:
        """
        Process level-up approval after AI and peer approvals.
        
        Checks that:
        1. AI Guild Master has approved the project
        2. Both peer reviewers have approved the project
        
        If all approvals are received, increments the user's level and updates
        the level-up request status to APPROVED.
        
        Implements Requirements:
        - 8.4: Dual approval level-up (AI + 2 peer approvals required)
        
        Args:
            levelup_request_id: Level-up request ID
            
        Returns:
            Dictionary with approval status:
            {
                'approved': bool,
                'user_id': str,
                'old_level': int,
                'new_level': int,
                'message': str
            }
            
        Raises:
            ValueError: If request not found
        """
        # Get level-up request
        levelup_request = self.db.query(LevelUpRequest).filter(
            LevelUpRequest.id == levelup_request_id
        ).first()
        
        if not levelup_request:
            raise ValueError(f"Level-up request {levelup_request_id} not found")
        
        # Get all assessments for this request
        assessments = self.db.query(ProjectAssessment).filter(
            ProjectAssessment.levelup_request_id == levelup_request_id
        ).all()
        
        # Check AI approval
        ai_assessments = [a for a in assessments if a.assessment_type == "ai"]
        ai_approved = any(a.approved == "true" for a in ai_assessments)
        
        # Check peer approvals (need exactly 2 approvals)
        peer_assessments = [a for a in assessments if a.assessment_type == "peer"]
        peer_approvals = [a for a in peer_assessments if a.approved == "true"]
        peer_approved = len(peer_approvals) >= 2
        
        # Check if all approvals received
        if not ai_approved:
            return {
                'approved': False,
                'user_id': str(levelup_request.user_id),
                'old_level': levelup_request.current_level,
                'new_level': levelup_request.current_level,
                'message': 'AI Guild Master approval required'
            }
        
        if not peer_approved:
            return {
                'approved': False,
                'user_id': str(levelup_request.user_id),
                'old_level': levelup_request.current_level,
                'new_level': levelup_request.current_level,
                'message': f'Peer approvals required (have {len(peer_approvals)}/2)'
            }
        
        # All approvals received - grant level-up
        user = self.db.query(User).filter(User.id == levelup_request.user_id).first()
        if not user:
            raise ValueError(f"User {levelup_request.user_id} not found")
        
        old_level = user.current_level
        new_level = levelup_request.target_level
        
        # Update user level
        user.current_level = new_level
        
        # Update level-up request status
        levelup_request.status = LevelUpStatus.APPROVED
        levelup_request.completed_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(
            f"Level-up approved for user {user.id}: "
            f"level {old_level} -> {new_level} "
            f"(request {levelup_request_id})"
        )
        
        return {
            'approved': True,
            'user_id': str(user.id),
            'old_level': old_level,
            'new_level': new_level,
            'message': f'Level-up approved! Congratulations on reaching level {new_level}!'
        }
    
    def provide_rejection_feedback(
        self,
        levelup_request_id: UUID,
        assessor_id: str,
        assessment_type: str,
        feedback: str
    ) -> ProjectAssessment:
        """
        Provide rejection feedback for a level-up project.
        
        Creates a ProjectAssessment with approved="false" and detailed feedback.
        Allows the user to resubmit after addressing the feedback.
        
        Implements Requirements:
        - 8.5: Rejection feedback provision and resubmission allowance
        
        Args:
            levelup_request_id: Level-up request ID
            assessor_id: ID of assessor ("guild_master_ai" or user UUID as string)
            assessment_type: "ai" or "peer"
            feedback: Detailed feedback explaining the rejection
            
        Returns:
            Created ProjectAssessment object
            
        Raises:
            ValueError: If request not found or feedback is empty
        """
        # Validate level-up request exists
        levelup_request = self.db.query(LevelUpRequest).filter(
            LevelUpRequest.id == levelup_request_id
        ).first()
        
        if not levelup_request:
            raise ValueError(f"Level-up request {levelup_request_id} not found")
        
        # Validate feedback is provided
        if not feedback or len(feedback.strip()) == 0:
            raise ValueError("Feedback is required for rejection")
        
        # Create rejection assessment
        assessment = ProjectAssessment(
            levelup_request_id=levelup_request_id,
            assessment_type=assessment_type,
            assessed_by=assessor_id,
            approved="false",
            feedback=feedback,
            assessed_at=datetime.utcnow()
        )
        
        self.db.add(assessment)
        
        # Update level-up request status to REJECTED
        levelup_request.status = LevelUpStatus.REJECTED
        levelup_request.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(
            f"Rejection feedback provided for level-up request {levelup_request_id} "
            f"by {assessor_id} ({assessment_type})"
        )
        
        return assessment
    
    def resubmit_levelup_project(
        self,
        user_id: UUID,
        previous_request_id: UUID,
        project_title: str,
        project_description: str,
        project_url: str
    ) -> LevelUpRequest:
        """
        Resubmit a level-up project after rejection.
        
        Creates a new level-up request after a previous one was rejected.
        The user can address the feedback from the rejection and resubmit.
        
        Implements Requirement 8.5: Allow resubmission after rejection.
        
        Args:
            user_id: ID of user resubmitting
            previous_request_id: ID of the rejected request
            project_title: Title of the revised project
            project_description: Updated description addressing feedback
            project_url: URL to revised project
            
        Returns:
            Created LevelUpRequest object
            
        Raises:
            ValueError: If user not found, previous request not rejected,
                       or user has pending request
        """
        # Validate previous request was rejected
        previous_request = self.db.query(LevelUpRequest).filter(
            LevelUpRequest.id == previous_request_id
        ).first()
        
        if not previous_request:
            raise ValueError(f"Previous level-up request {previous_request_id} not found")
        
        if previous_request.status != LevelUpStatus.REJECTED:
            raise ValueError(
                f"Previous request {previous_request_id} was not rejected "
                f"(status: {previous_request.status})"
            )
        
        if previous_request.user_id != user_id:
            raise ValueError(
                f"Previous request {previous_request_id} does not belong to user {user_id}"
            )
        
        # Create new level-up request (reuses submit_levelup_project logic)
        new_request = self.submit_levelup_project(
            user_id=user_id,
            project_title=project_title,
            project_description=project_description,
            project_url=project_url
        )
        
        logger.info(
            f"Level-up project resubmitted by user {user_id}. "
            f"Previous request: {previous_request_id}, new request: {new_request.id}"
        )
        
        return new_request
