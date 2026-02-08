"""
Tests for Mool reputation system service.

Tests the business logic for work submission, peer review, and reputation management.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.mool_service import MoolService
from app.models.user import User, UserProfile
from app.models.guild import Guild, GuildMembership, GuildType
from app.models.squad import Squad, SquadMembership, SquadStatus
from app.models.mool import WorkSubmission, PeerReview


class TestMoolService:
    """Test suite for MoolService."""
    
    def test_submit_work_for_review_success(self, test_db):
        """Test successful work submission for review."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create squad
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE,
            member_count=12
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter user
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        test_db.flush()
        
        # Create submitter profile
        submitter_profile = UserProfile(
            user_id=submitter.id,
            display_name="Submitter",
            interest_area="Python Programming",
            skill_level=5,
            timezone="America/New_York",
            preferred_language="en"
        )
        test_db.add(submitter_profile)
        
        # Add submitter to guild and squad
        guild_membership = GuildMembership(
            user_id=submitter.id,
            guild_id=guild.id
        )
        test_db.add(guild_membership)
        
        squad_membership = SquadMembership(
            user_id=submitter.id,
            squad_id=squad.id
        )
        test_db.add(squad_membership)
        test_db.commit()
        
        # Create service
        service = MoolService(test_db)
        
        # Submit work
        submission = service.submit_work_for_review(
            user_id=submitter.id,
            squad_id=squad.id,
            title="My Python Project",
            description="A comprehensive Python project demonstrating OOP principles",
            submission_url="https://github.com/user/project"
        )
        
        # Assertions
        assert submission.id is not None
        assert submission.user_id == submitter.id
        assert submission.squad_id == squad.id
        assert submission.title == "My Python Project"
        assert submission.description == "A comprehensive Python project demonstrating OOP principles"
        assert submission.submission_url == "https://github.com/user/project"
        assert submission.submitted_at is not None
        assert isinstance(submission.submitted_at, datetime)
    
    def test_submit_work_user_not_found(self, test_db):
        """Test work submission fails when user doesn't exist."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.commit()
        
        service = MoolService(test_db)
        
        # Try to submit with non-existent user
        with pytest.raises(ValueError, match="User .* not found"):
            service.submit_work_for_review(
                user_id=uuid4(),
                squad_id=squad.id,
                title="Test",
                description="Test",
                submission_url="https://test.com"
            )
    
    def test_submit_work_squad_not_found(self, test_db):
        """Test work submission fails when squad doesn't exist."""
        # Create user
        user = User(email="user@test.com")
        user.set_password("password123")
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        
        # Try to submit with non-existent squad
        with pytest.raises(ValueError, match="Squad .* not found"):
            service.submit_work_for_review(
                user_id=user.id,
                squad_id=uuid4(),
                title="Test",
                description="Test",
                submission_url="https://test.com"
            )
    
    def test_submit_work_user_not_in_squad(self, test_db):
        """Test work submission fails when user is not a member of the squad."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create squad
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create user (not in squad)
        user = User(email="user@test.com")
        user.set_password("password123")
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        
        # Try to submit work
        with pytest.raises(ValueError, match="User .* is not a member of squad"):
            service.submit_work_for_review(
                user_id=user.id,
                squad_id=squad.id,
                title="Test",
                description="Test",
                submission_url="https://test.com"
            )
    
    def test_get_eligible_reviewers_excludes_squad_members(self, test_db):
        """Test that eligible reviewers excludes direct collaborators (same squad)."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create two squads in the same guild
        squad1 = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE,
            member_count=3
        )
        squad2 = Squad(
            guild_id=guild.id,
            name="Squad Beta",
            status=SquadStatus.ACTIVE,
            member_count=2
        )
        test_db.add_all([squad1, squad2])
        test_db.flush()
        
        # Create users
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        
        squad1_member1 = User(email="squad1_member1@test.com")
        squad1_member1.set_password("password123")
        
        squad1_member2 = User(email="squad1_member2@test.com")
        squad1_member2.set_password("password123")
        
        squad2_member1 = User(email="squad2_member1@test.com")
        squad2_member1.set_password("password123")
        
        squad2_member2 = User(email="squad2_member2@test.com")
        squad2_member2.set_password("password123")
        
        test_db.add_all([submitter, squad1_member1, squad1_member2, squad2_member1, squad2_member2])
        test_db.flush()
        
        # Add all users to guild
        for user in [submitter, squad1_member1, squad1_member2, squad2_member1, squad2_member2]:
            guild_membership = GuildMembership(
                user_id=user.id,
                guild_id=guild.id
            )
            test_db.add(guild_membership)
        
        # Add users to squads
        # Squad 1: submitter, squad1_member1, squad1_member2
        for user in [submitter, squad1_member1, squad1_member2]:
            squad_membership = SquadMembership(
                user_id=user.id,
                squad_id=squad1.id
            )
            test_db.add(squad_membership)
        
        # Squad 2: squad2_member1, squad2_member2
        for user in [squad2_member1, squad2_member2]:
            squad_membership = SquadMembership(
                user_id=user.id,
                squad_id=squad2.id
            )
            test_db.add(squad_membership)
        
        test_db.commit()
        
        # Create work submission from submitter in squad1
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad1.id,
            title="Test Submission",
            description="Test",
            submission_url="https://test.com"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Get eligible reviewers
        service = MoolService(test_db)
        eligible_reviewers = service.get_eligible_reviewers(submission)
        
        # Assertions
        # Should only include squad2 members (not squad1 members or submitter)
        eligible_ids = {reviewer.id for reviewer in eligible_reviewers}
        assert len(eligible_reviewers) == 2
        assert squad2_member1.id in eligible_ids
        assert squad2_member2.id in eligible_ids
        assert submitter.id not in eligible_ids
        assert squad1_member1.id not in eligible_ids
        assert squad1_member2.id not in eligible_ids
    
    def test_get_eligible_reviewers_empty_when_no_other_squads(self, test_db):
        """Test that eligible reviewers is empty when guild has only one squad."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create single squad
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE,
            member_count=2
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create users in the squad
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        
        member = User(email="member@test.com")
        member.set_password("password123")
        
        test_db.add_all([submitter, member])
        test_db.flush()
        
        # Add to guild and squad
        for user in [submitter, member]:
            guild_membership = GuildMembership(
                user_id=user.id,
                guild_id=guild.id
            )
            test_db.add(guild_membership)
            
            squad_membership = SquadMembership(
                user_id=user.id,
                squad_id=squad.id
            )
            test_db.add(squad_membership)
        
        test_db.commit()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Submission",
            description="Test",
            submission_url="https://test.com"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Get eligible reviewers
        service = MoolService(test_db)
        eligible_reviewers = service.get_eligible_reviewers(submission)
        
        # Should be empty (no other squads in guild)
        assert len(eligible_reviewers) == 0
    
    def test_calculate_reputation_award_base_case(self, test_db):
        """Test reputation calculation with base case (no bonuses)."""
        service = MoolService(test_db)
        
        # Base case: level 1 reviewer, short review, slow response
        submission_time = datetime.utcnow()
        review_time = submission_time + timedelta(hours=48)
        review_content = "Good work"  # < 200 words
        reviewer_level = 1
        
        points = service.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer_level,
            submission_time=submission_time,
            review_time=review_time
        )
        
        # Expected: 10 * (1 + 1 * 0.1) = 10 * 1.1 = 11
        assert points == 11
    
    def test_calculate_reputation_award_with_quality_bonus(self, test_db):
        """Test reputation calculation with quality bonus."""
        service = MoolService(test_db)
        
        # Long review (> 200 words)
        submission_time = datetime.utcnow()
        review_time = submission_time + timedelta(hours=48)
        review_content = " ".join(["word"] * 201)  # 201 words
        reviewer_level = 1
        
        points = service.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer_level,
            submission_time=submission_time,
            review_time=review_time
        )
        
        # Expected: 10 * 1.1 + 5 (quality bonus) = 16
        assert points == 16
    
    def test_calculate_reputation_award_with_consistency_bonus(self, test_db):
        """Test reputation calculation with consistency bonus."""
        service = MoolService(test_db)
        
        # Quick review (< 24 hours)
        submission_time = datetime.utcnow()
        review_time = submission_time + timedelta(hours=12)
        review_content = "Good work"  # < 200 words
        reviewer_level = 1
        
        points = service.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer_level,
            submission_time=submission_time,
            review_time=review_time
        )
        
        # Expected: 10 * 1.1 + 3 (consistency bonus) = 14
        assert points == 14
    
    def test_calculate_reputation_award_with_all_bonuses(self, test_db):
        """Test reputation calculation with all bonuses."""
        service = MoolService(test_db)
        
        # High level reviewer, long review, quick response
        submission_time = datetime.utcnow()
        review_time = submission_time + timedelta(hours=12)
        review_content = " ".join(["word"] * 201)  # 201 words
        reviewer_level = 5
        
        points = service.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer_level,
            submission_time=submission_time,
            review_time=review_time
        )
        
        # Expected: 10 * (1 + 5 * 0.1) + 5 + 3 = 10 * 1.5 + 8 = 15 + 8 = 23
        assert points == 23
    
    def test_calculate_reputation_award_capped_at_25(self, test_db):
        """Test reputation calculation is capped at 25 points."""
        service = MoolService(test_db)
        
        # Very high level reviewer with all bonuses
        submission_time = datetime.utcnow()
        review_time = submission_time + timedelta(hours=1)
        review_content = " ".join(["word"] * 300)  # 300 words
        reviewer_level = 10  # Very high level
        
        points = service.calculate_reputation_award(
            review_content=review_content,
            reviewer_level=reviewer_level,
            submission_time=submission_time,
            review_time=review_time
        )
        
        # Expected: 10 * (1 + 10 * 0.1) + 5 + 3 = 10 * 2 + 8 = 28, capped at 25
        assert points == 25
    
    def test_get_user_reputation(self, test_db):
        """Test getting user's total reputation points."""
        # Create user with reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.reputation_points = 150
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        reputation = service.get_user_reputation(user.id)
        
        assert reputation == 150
    
    def test_get_user_reputation_user_not_found(self, test_db):
        """Test getting reputation for non-existent user raises error."""
        service = MoolService(test_db)
        
        with pytest.raises(ValueError, match="User .* not found"):
            service.get_user_reputation(uuid4())
    
    def test_submit_peer_review_success(self, test_db):
        """Test successful peer review submission and reputation award."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create squad
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        submitter.reputation_points = 0
        test_db.add(submitter)
        test_db.flush()
        
        # Create reviewer
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 50  # Starting reputation
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project",
            submitted_at=datetime.utcnow()
        )
        test_db.add(submission)
        test_db.commit()
        
        # Submit peer review
        service = MoolService(test_db)
        review = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission.id,
            review_content="Great work! Well structured code.",
            rating=4
        )
        
        # Assertions
        assert review.id is not None
        assert review.submission_id == submission.id
        assert review.reviewer_id == reviewer.id
        assert review.review_content == "Great work! Well structured code."
        assert review.rating == 4
        assert review.reputation_awarded > 0
        assert review.submitted_at is not None
        
        # Check reviewer's reputation was updated
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == 50 + review.reputation_awarded
    
    def test_submit_peer_review_with_quality_bonus(self, test_db):
        """Test peer review with quality bonus (> 200 words)."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 5
        reviewer.reputation_points = 100
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project",
            submitted_at=datetime.utcnow()
        )
        test_db.add(submission)
        test_db.commit()
        
        # Submit detailed review (> 200 words)
        long_review = " ".join(["word"] * 201)
        service = MoolService(test_db)
        review = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission.id,
            review_content=long_review,
            rating=5
        )
        
        # Expected: 10 * (1 + 5 * 0.1) + 5 (quality bonus) = 10 * 1.5 + 5 = 20
        assert review.reputation_awarded == 20
        
        # Check reputation was awarded
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == 120  # 100 + 20
    
    def test_submit_peer_review_with_consistency_bonus(self, test_db):
        """Test peer review with consistency bonus (< 24 hours)."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 75
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission submitted recently (< 24 hours ago)
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project",
            submitted_at=datetime.utcnow() - timedelta(hours=12)
        )
        test_db.add(submission)
        test_db.commit()
        
        # Submit review quickly
        service = MoolService(test_db)
        review = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission.id,
            review_content="Good work",
            rating=4
        )
        
        # Expected: 10 * (1 + 3 * 0.1) + 3 (consistency bonus) = 10 * 1.3 + 3 = 16
        assert review.reputation_awarded == 16
        
        # Check reputation was awarded
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == 91  # 75 + 16
    
    def test_submit_peer_review_with_all_bonuses(self, test_db):
        """Test peer review with both quality and consistency bonuses."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and high-level reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 5
        reviewer.reputation_points = 200
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission submitted recently
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project",
            submitted_at=datetime.utcnow() - timedelta(hours=6)
        )
        test_db.add(submission)
        test_db.commit()
        
        # Submit detailed, quick review
        long_review = " ".join(["word"] * 250)
        service = MoolService(test_db)
        review = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission.id,
            review_content=long_review,
            rating=5
        )
        
        # Expected: 10 * (1 + 5 * 0.1) + 5 + 3 = 10 * 1.5 + 8 = 23
        assert review.reputation_awarded == 23
        
        # Check reputation was awarded
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == 223  # 200 + 23
    
    def test_submit_peer_review_capped_at_25(self, test_db):
        """Test peer review reputation is capped at 25 points."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and very high-level reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 10  # Very high level
        reviewer.reputation_points = 500
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project",
            submitted_at=datetime.utcnow() - timedelta(hours=1)
        )
        test_db.add(submission)
        test_db.commit()
        
        # Submit detailed, quick review
        long_review = " ".join(["word"] * 300)
        service = MoolService(test_db)
        review = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission.id,
            review_content=long_review,
            rating=5
        )
        
        # Expected: 10 * (1 + 10 * 0.1) + 5 + 3 = 28, capped at 25
        assert review.reputation_awarded == 25
        
        # Check reputation was awarded
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == 525  # 500 + 25
    
    def test_submit_peer_review_reviewer_not_found(self, test_db):
        """Test peer review submission fails when reviewer doesn't exist."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        test_db.add(submitter)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Try to submit review with non-existent reviewer
        service = MoolService(test_db)
        with pytest.raises(ValueError, match="Reviewer .* not found"):
            service.submit_peer_review(
                reviewer_id=uuid4(),
                submission_id=submission.id,
                review_content="Test review",
                rating=4
            )
    
    def test_submit_peer_review_submission_not_found(self, test_db):
        """Test peer review submission fails when work submission doesn't exist."""
        # Create reviewer
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        test_db.add(reviewer)
        test_db.commit()
        
        # Try to submit review for non-existent submission
        service = MoolService(test_db)
        with pytest.raises(ValueError, match="Work submission .* not found"):
            service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=uuid4(),
                review_content="Test review",
                rating=4
            )
    
    def test_submit_peer_review_invalid_rating(self, test_db):
        """Test peer review submission fails with invalid rating."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        test_db.add(reviewer)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Try to submit review with invalid rating (too low)
        service = MoolService(test_db)
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=submission.id,
                review_content="Test review",
                rating=0
            )
        
        # Try to submit review with invalid rating (too high)
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=submission.id,
                review_content="Test review",
                rating=6
            )
    
    def test_submit_peer_review_multiple_reviews_accumulate(self, test_db):
        """Test that multiple reviews accumulate reputation points."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 0  # Start at 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Create multiple work submissions
        submission1 = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Project 1",
            description="First project",
            submission_url="https://github.com/test/project1",
            submitted_at=datetime.utcnow()
        )
        submission2 = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Project 2",
            description="Second project",
            submission_url="https://github.com/test/project2",
            submitted_at=datetime.utcnow()
        )
        test_db.add_all([submission1, submission2])
        test_db.commit()
        
        # Submit first review
        service = MoolService(test_db)
        review1 = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission1.id,
            review_content="Good work on project 1",
            rating=4
        )
        
        test_db.refresh(reviewer)
        first_reputation = reviewer.reputation_points
        assert first_reputation == review1.reputation_awarded
        
        # Submit second review
        review2 = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission2.id,
            review_content="Excellent work on project 2",
            rating=5
        )
        
        test_db.refresh(reviewer)
        assert reviewer.reputation_points == first_reputation + review2.reputation_awarded


class TestReputationTracking:
    """Test suite for reputation tracking and display functionality."""
    
    def test_get_user_reputation_returns_stored_value(self, test_db):
        """Test that get_user_reputation returns the stored reputation_points value."""
        # Create user with reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.reputation_points = 250
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        reputation = service.get_user_reputation(user.id)
        
        assert reputation == 250
    
    def test_get_user_reputation_zero_for_new_user(self, test_db):
        """Test that new users have zero reputation."""
        # Create new user
        user = User(email="newuser@test.com")
        user.set_password("password123")
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        reputation = service.get_user_reputation(user.id)
        
        assert reputation == 0
    
    def test_calculate_reputation_from_reviews_matches_stored(self, test_db):
        """Test that calculated reputation from reviews matches stored value."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Create multiple submissions and reviews
        service = MoolService(test_db)
        
        for i in range(3):
            submission = WorkSubmission(
                user_id=submitter.id,
                squad_id=squad.id,
                title=f"Project {i+1}",
                description=f"Project {i+1} description",
                submission_url=f"https://github.com/test/project{i+1}",
                submitted_at=datetime.utcnow()
            )
            test_db.add(submission)
            test_db.flush()
            
            service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=submission.id,
                review_content=f"Review for project {i+1}",
                rating=4
            )
        
        test_db.refresh(reviewer)
        
        # Calculate reputation from reviews
        calculated_reputation = service.calculate_user_reputation_from_reviews(reviewer.id)
        
        # Should match stored value
        assert calculated_reputation == reviewer.reputation_points
        assert calculated_reputation > 0
    
    def test_calculate_reputation_from_reviews_zero_for_no_reviews(self, test_db):
        """Test that calculated reputation is zero when user has no reviews."""
        # Create user with no reviews
        user = User(email="user@test.com")
        user.set_password("password123")
        user.reputation_points = 0
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        calculated_reputation = service.calculate_user_reputation_from_reviews(user.id)
        
        assert calculated_reputation == 0
    
    def test_calculate_reputation_from_reviews_user_not_found(self, test_db):
        """Test that calculating reputation for non-existent user raises error."""
        service = MoolService(test_db)
        
        with pytest.raises(ValueError, match="User .* not found"):
            service.calculate_user_reputation_from_reviews(uuid4())
    
    def test_get_reputation_breakdown_complete_info(self, test_db):
        """Test that reputation breakdown provides complete information."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Create submissions and reviews
        service = MoolService(test_db)
        review_ids = []
        
        for i in range(5):
            submission = WorkSubmission(
                user_id=submitter.id,
                squad_id=squad.id,
                title=f"Project {i+1}",
                description=f"Project {i+1} description",
                submission_url=f"https://github.com/test/project{i+1}",
                submitted_at=datetime.utcnow()
            )
            test_db.add(submission)
            test_db.flush()
            
            review = service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=submission.id,
                review_content=f"Review for project {i+1}",
                rating=4
            )
            review_ids.append(review.id)
        
        # Get reputation breakdown
        breakdown = service.get_user_reputation_breakdown(reviewer.id)
        
        # Assertions
        assert 'total_reputation' in breakdown
        assert 'review_count' in breakdown
        assert 'average_per_review' in breakdown
        assert 'recent_reviews' in breakdown
        
        assert breakdown['review_count'] == 5
        assert breakdown['total_reputation'] > 0
        assert breakdown['average_per_review'] > 0
        assert len(breakdown['recent_reviews']) == 5
        
        # Check recent reviews structure
        for recent_review in breakdown['recent_reviews']:
            assert 'review_id' in recent_review
            assert 'submission_id' in recent_review
            assert 'reputation_awarded' in recent_review
            assert 'rating' in recent_review
            assert 'submitted_at' in recent_review
    
    def test_get_reputation_breakdown_empty_for_no_reviews(self, test_db):
        """Test that reputation breakdown works for users with no reviews."""
        # Create user with no reviews
        user = User(email="user@test.com")
        user.set_password("password123")
        user.reputation_points = 0
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        breakdown = service.get_user_reputation_breakdown(user.id)
        
        assert breakdown['total_reputation'] == 0
        assert breakdown['review_count'] == 0
        assert breakdown['average_per_review'] == 0.0
        assert len(breakdown['recent_reviews']) == 0
    
    def test_get_reputation_breakdown_limits_recent_reviews(self, test_db):
        """Test that reputation breakdown limits recent reviews to 10."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Create 15 submissions and reviews
        service = MoolService(test_db)
        
        for i in range(15):
            submission = WorkSubmission(
                user_id=submitter.id,
                squad_id=squad.id,
                title=f"Project {i+1}",
                description=f"Project {i+1} description",
                submission_url=f"https://github.com/test/project{i+1}",
                submitted_at=datetime.utcnow()
            )
            test_db.add(submission)
            test_db.flush()
            
            service.submit_peer_review(
                reviewer_id=reviewer.id,
                submission_id=submission.id,
                review_content=f"Review for project {i+1}",
                rating=4
            )
        
        # Get reputation breakdown
        breakdown = service.get_user_reputation_breakdown(reviewer.id)
        
        # Should have 15 total reviews but only 10 recent
        assert breakdown['review_count'] == 15
        assert len(breakdown['recent_reviews']) == 10
    
    def test_get_reputation_breakdown_user_not_found(self, test_db):
        """Test that getting breakdown for non-existent user raises error."""
        service = MoolService(test_db)
        
        with pytest.raises(ValueError, match="User .* not found"):
            service.get_user_reputation_breakdown(uuid4())
    
    def test_reputation_aggregation_property(self, test_db):
        """
        Test Property 25: Reputation Point Aggregation
        
        For any user, the total reputation points displayed on their profile
        should equal the sum of all individual reputation awards.
        
        Validates: Requirements 7.4
        """
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 4
        reviewer.reputation_points = 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Create multiple submissions and reviews with varying characteristics
        service = MoolService(test_db)
        expected_total = 0
        
        # Review 1: Base case
        submission1 = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Project 1",
            description="Project 1",
            submission_url="https://github.com/test/project1",
            submitted_at=datetime.utcnow() - timedelta(hours=48)
        )
        test_db.add(submission1)
        test_db.flush()
        
        review1 = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission1.id,
            review_content="Good work",
            rating=4
        )
        expected_total += review1.reputation_awarded
        
        # Review 2: With quality bonus
        submission2 = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Project 2",
            description="Project 2",
            submission_url="https://github.com/test/project2",
            submitted_at=datetime.utcnow() - timedelta(hours=48)
        )
        test_db.add(submission2)
        test_db.flush()
        
        review2 = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission2.id,
            review_content=" ".join(["word"] * 201),  # > 200 words
            rating=5
        )
        expected_total += review2.reputation_awarded
        
        # Review 3: With consistency bonus
        submission3 = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Project 3",
            description="Project 3",
            submission_url="https://github.com/test/project3",
            submitted_at=datetime.utcnow() - timedelta(hours=12)
        )
        test_db.add(submission3)
        test_db.flush()
        
        review3 = service.submit_peer_review(
            reviewer_id=reviewer.id,
            submission_id=submission3.id,
            review_content="Quick review",
            rating=4
        )
        expected_total += review3.reputation_awarded
        
        # Verify Property 25: Total reputation equals sum of all awards
        test_db.refresh(reviewer)
        displayed_reputation = service.get_user_reputation(reviewer.id)
        calculated_reputation = service.calculate_user_reputation_from_reviews(reviewer.id)
        
        # All three should match
        assert displayed_reputation == expected_total
        assert calculated_reputation == expected_total
        assert reviewer.reputation_points == expected_total
        
        # Verify breakdown also matches
        breakdown = service.get_user_reputation_breakdown(reviewer.id)
        assert breakdown['total_reputation'] == expected_total
        assert breakdown['review_count'] == 3



class TestReviewerPrivilegeUnlocking:
    """Test suite for reviewer privilege unlocking functionality."""
    
    def test_unlock_reviewer_privileges_base_level(self, test_db):
        """Test reviewer privileges at base level (0 reputation)."""
        # Create user with no reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 3
        user.reputation_points = 0
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 0 reputation, can only review own level or below
        assert privileges['user_id'] == str(user.id)
        assert privileges['current_level'] == 3
        assert privileges['reputation_points'] == 0
        assert privileges['max_reviewable_level'] == 3  # Own level
        assert privileges['levels_above_unlocked'] == 0
        assert privileges['next_unlock_at'] == 50
        assert privileges['next_unlock_levels'] == 1
    
    def test_unlock_reviewer_privileges_first_threshold(self, test_db):
        """Test reviewer privileges at first threshold (50 reputation)."""
        # Create user with 50 reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 3
        user.reputation_points = 50
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 50 reputation, can review 1 level above
        assert privileges['current_level'] == 3
        assert privileges['reputation_points'] == 50
        assert privileges['max_reviewable_level'] == 4  # 1 level above
        assert privileges['levels_above_unlocked'] == 1
        assert privileges['next_unlock_at'] == 150
        assert privileges['next_unlock_levels'] == 2
    
    def test_unlock_reviewer_privileges_second_threshold(self, test_db):
        """Test reviewer privileges at second threshold (150 reputation)."""
        # Create user with 150 reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 3
        user.reputation_points = 150
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 150 reputation, can review 2 levels above
        assert privileges['current_level'] == 3
        assert privileges['reputation_points'] == 150
        assert privileges['max_reviewable_level'] == 5  # 2 levels above
        assert privileges['levels_above_unlocked'] == 2
        assert privileges['next_unlock_at'] == 300
        assert privileges['next_unlock_levels'] == 3
    
    def test_unlock_reviewer_privileges_third_threshold(self, test_db):
        """Test reviewer privileges at third threshold (300 reputation)."""
        # Create user with 300 reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 2
        user.reputation_points = 300
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 300 reputation, can review 3 levels above
        assert privileges['current_level'] == 2
        assert privileges['reputation_points'] == 300
        assert privileges['max_reviewable_level'] == 5  # 3 levels above
        assert privileges['levels_above_unlocked'] == 3
        assert privileges['next_unlock_at'] == 500
        assert privileges['next_unlock_levels'] == 4
    
    def test_unlock_reviewer_privileges_fourth_threshold(self, test_db):
        """Test reviewer privileges at fourth threshold (500 reputation)."""
        # Create user with 500 reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 1
        user.reputation_points = 500
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 500 reputation, can review 4 levels above
        assert privileges['current_level'] == 1
        assert privileges['reputation_points'] == 500
        assert privileges['max_reviewable_level'] == 5  # 4 levels above
        assert privileges['levels_above_unlocked'] == 4
        assert privileges['next_unlock_at'] == 750
        assert privileges['next_unlock_levels'] == 5
    
    def test_unlock_reviewer_privileges_max_threshold(self, test_db):
        """Test reviewer privileges at max threshold (750+ reputation)."""
        # Create user with 750+ reputation
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 2
        user.reputation_points = 1000
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 750+ reputation, can review 5+ levels above
        assert privileges['current_level'] == 2
        assert privileges['reputation_points'] == 1000
        assert privileges['max_reviewable_level'] == 7  # 2 + 5
        assert privileges['levels_above_unlocked'] == 5
        assert privileges['next_unlock_at'] is None  # No more thresholds
        assert privileges['next_unlock_levels'] is None
    
    def test_unlock_reviewer_privileges_user_not_found(self, test_db):
        """Test unlock reviewer privileges fails when user doesn't exist."""
        service = MoolService(test_db)
        
        with pytest.raises(ValueError, match="User .* not found"):
            service.unlock_reviewer_privileges(uuid4())
    
    def test_unlock_reviewer_privileges_between_thresholds(self, test_db):
        """Test reviewer privileges between thresholds (e.g., 100 reputation)."""
        # Create user with 100 reputation (between 50 and 150)
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 4
        user.reputation_points = 100
        test_db.add(user)
        test_db.commit()
        
        service = MoolService(test_db)
        privileges = service.unlock_reviewer_privileges(user.id)
        
        # At 100 reputation, still at first threshold (50 points)
        assert privileges['current_level'] == 4
        assert privileges['reputation_points'] == 100
        assert privileges['max_reviewable_level'] == 5  # 1 level above
        assert privileges['levels_above_unlocked'] == 1
        assert privileges['next_unlock_at'] == 150
        assert privileges['next_unlock_levels'] == 2


class TestCanReviewSubmission:
    """Test suite for can_review_submission functionality."""
    
    def test_can_review_submission_success(self, test_db):
        """Test successful review eligibility check."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create two squads
        squad1 = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        squad2 = Squad(
            guild_id=guild.id,
            name="Squad Beta",
            status=SquadStatus.ACTIVE
        )
        test_db.add_all([squad1, squad2])
        test_db.flush()
        
        # Create submitter (level 2, in squad1)
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        test_db.flush()
        
        # Create reviewer (level 3, 50 reputation, in squad2)
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 50  # Can review 1 level above (up to level 4)
        test_db.add(reviewer)
        test_db.flush()
        
        # Add users to squads
        squad1_membership = SquadMembership(
            user_id=submitter.id,
            squad_id=squad1.id
        )
        squad2_membership = SquadMembership(
            user_id=reviewer.id,
            squad_id=squad2.id
        )
        test_db.add_all([squad1_membership, squad2_membership])
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad1.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if reviewer can review
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(reviewer.id, submission.id)
        
        # Should be able to review (different squads, submitter level 2 <= reviewer max level 4)
        assert can_review is True
        assert reason == "Eligible to review this submission"
    
    def test_can_review_submission_own_submission(self, test_db):
        """Test cannot review own submission."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create user
        user = User(email="user@test.com")
        user.set_password("password123")
        user.current_level = 3
        user.reputation_points = 100
        test_db.add(user)
        test_db.flush()
        
        # Create work submission by same user
        submission = WorkSubmission(
            user_id=user.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if user can review their own submission
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(user.id, submission.id)
        
        # Should not be able to review own submission
        assert can_review is False
        assert reason == "Cannot review your own submission"
    
    def test_can_review_submission_same_squad(self, test_db):
        """Test cannot review submission from same squad (collaborators)."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create squad
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter and reviewer (both in same squad)
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 100
        test_db.add(reviewer)
        test_db.flush()
        
        # Add both to same squad
        for user in [submitter, reviewer]:
            membership = SquadMembership(
                user_id=user.id,
                squad_id=squad.id
            )
            test_db.add(membership)
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if reviewer can review
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(reviewer.id, submission.id)
        
        # Should not be able to review (same squad = collaborators)
        assert can_review is False
        assert reason == "Cannot review submissions from squad members (direct collaborators)"
    
    def test_can_review_submission_insufficient_reputation(self, test_db):
        """Test cannot review submission from higher-level user without enough reputation."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create two squads
        squad1 = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        squad2 = Squad(
            guild_id=guild.id,
            name="Squad Beta",
            status=SquadStatus.ACTIVE
        )
        test_db.add_all([squad1, squad2])
        test_db.flush()
        
        # Create high-level submitter (level 5, in squad1)
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 5
        test_db.add(submitter)
        test_db.flush()
        
        # Create low-level reviewer (level 2, 0 reputation, in squad2)
        # With 0 reputation, can only review up to level 2
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 2
        reviewer.reputation_points = 0
        test_db.add(reviewer)
        test_db.flush()
        
        # Add users to squads
        squad1_membership = SquadMembership(
            user_id=submitter.id,
            squad_id=squad1.id
        )
        squad2_membership = SquadMembership(
            user_id=reviewer.id,
            squad_id=squad2.id
        )
        test_db.add_all([squad1_membership, squad2_membership])
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad1.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if reviewer can review
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(reviewer.id, submission.id)
        
        # Should not be able to review (submitter level 5 > reviewer max level 2)
        assert can_review is False
        assert "Insufficient reputation" in reason
        assert "level 5" in reason
        assert "level 2" in reason
    
    def test_can_review_submission_with_reputation_unlocks_higher_level(self, test_db):
        """Test that reputation unlocks ability to review higher-level submissions."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create two squads
        squad1 = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        squad2 = Squad(
            guild_id=guild.id,
            name="Squad Beta",
            status=SquadStatus.ACTIVE
        )
        test_db.add_all([squad1, squad2])
        test_db.flush()
        
        # Create submitter (level 4, in squad1)
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 4
        test_db.add(submitter)
        test_db.flush()
        
        # Create reviewer (level 2, 150 reputation, in squad2)
        # With 150 reputation, can review 2 levels above (up to level 4)
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 2
        reviewer.reputation_points = 150
        test_db.add(reviewer)
        test_db.flush()
        
        # Add users to squads
        squad1_membership = SquadMembership(
            user_id=submitter.id,
            squad_id=squad1.id
        )
        squad2_membership = SquadMembership(
            user_id=reviewer.id,
            squad_id=squad2.id
        )
        test_db.add_all([squad1_membership, squad2_membership])
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad1.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if reviewer can review
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(reviewer.id, submission.id)
        
        # Should be able to review (submitter level 4 <= reviewer max level 4)
        assert can_review is True
        assert reason == "Eligible to review this submission"
    
    def test_can_review_submission_reviewer_not_found(self, test_db):
        """Test can_review_submission fails when reviewer doesn't exist."""
        # Create guild and squad
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        squad = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        test_db.add(squad)
        test_db.flush()
        
        # Create submitter
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 2
        test_db.add(submitter)
        test_db.flush()
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Try to check with non-existent reviewer
        service = MoolService(test_db)
        with pytest.raises(ValueError, match="Reviewer .* not found"):
            service.can_review_submission(uuid4(), submission.id)
    
    def test_can_review_submission_submission_not_found(self, test_db):
        """Test can_review_submission fails when submission doesn't exist."""
        # Create reviewer
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 100
        test_db.add(reviewer)
        test_db.commit()
        
        # Try to check with non-existent submission
        service = MoolService(test_db)
        with pytest.raises(ValueError, match="Work submission .* not found"):
            service.can_review_submission(reviewer.id, uuid4())
    
    def test_can_review_submission_at_reputation_boundary(self, test_db):
        """Test review eligibility at exact reputation threshold boundaries."""
        # Create guild
        guild = Guild(
            name="Python Masters",
            interest_area="Python Programming",
            guild_type=GuildType.PUBLIC
        )
        test_db.add(guild)
        test_db.flush()
        
        # Create two squads
        squad1 = Squad(
            guild_id=guild.id,
            name="Squad Alpha",
            status=SquadStatus.ACTIVE
        )
        squad2 = Squad(
            guild_id=guild.id,
            name="Squad Beta",
            status=SquadStatus.ACTIVE
        )
        test_db.add_all([squad1, squad2])
        test_db.flush()
        
        # Create submitter (level 4, in squad1)
        submitter = User(email="submitter@test.com")
        submitter.set_password("password123")
        submitter.current_level = 4
        test_db.add(submitter)
        test_db.flush()
        
        # Create reviewer (level 3, exactly 50 reputation, in squad2)
        # With exactly 50 reputation, can review 1 level above (up to level 4)
        reviewer = User(email="reviewer@test.com")
        reviewer.set_password("password123")
        reviewer.current_level = 3
        reviewer.reputation_points = 50  # Exactly at threshold
        test_db.add(reviewer)
        test_db.flush()
        
        # Add users to squads
        squad1_membership = SquadMembership(
            user_id=submitter.id,
            squad_id=squad1.id
        )
        squad2_membership = SquadMembership(
            user_id=reviewer.id,
            squad_id=squad2.id
        )
        test_db.add_all([squad1_membership, squad2_membership])
        
        # Create work submission
        submission = WorkSubmission(
            user_id=submitter.id,
            squad_id=squad1.id,
            title="Test Project",
            description="A test project",
            submission_url="https://github.com/test/project"
        )
        test_db.add(submission)
        test_db.commit()
        
        # Check if reviewer can review
        service = MoolService(test_db)
        can_review, reason = service.can_review_submission(reviewer.id, submission.id)
        
        # Should be able to review (submitter level 4 <= reviewer max level 4)
        assert can_review is True
        assert reason == "Eligible to review this submission"
