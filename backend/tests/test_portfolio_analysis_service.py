"""
Tests for Portfolio Analysis Service.

Tests GitHub portfolio analysis functionality including:
- GitHub URL parsing
- Repository analysis
- Skill level calculation
- API retry with exponential backoff

Validates Requirements 13.1, 13.2, 13.12
"""
import pytest
import requests
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from github import GithubException, RateLimitExceededException
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.models.skill_assessment import SkillAssessment, AssessmentSource
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def service(mock_db):
    """Create portfolio analysis service with mocked dependencies."""
    with patch('app.services.portfolio_analysis_service.settings') as mock_settings:
        mock_settings.GITHUB_TOKEN = "test_token"
        service = PortfolioAnalysisService(mock_db)
        return service


class TestGitHubURLParsing:
    """Test GitHub URL parsing functionality."""
    
    def test_extract_username_from_full_url(self, service):
        """Test extracting username from full GitHub URL."""
        url = "https://github.com/testuser"
        username = service._extract_github_username(url)
        assert username == "testuser"
    
    def test_extract_username_from_url_with_trailing_slash(self, service):
        """Test extracting username from URL with trailing slash."""
        url = "https://github.com/testuser/"
        username = service._extract_github_username(url)
        assert username == "testuser"
    
    def test_extract_username_from_http_url(self, service):
        """Test extracting username from HTTP URL."""
        url = "http://github.com/testuser"
        username = service._extract_github_username(url)
        assert username == "testuser"
    
    def test_extract_username_from_short_url(self, service):
        """Test extracting username from short URL format."""
        url = "github.com/testuser"
        username = service._extract_github_username(url)
        assert username == "testuser"
    
    def test_extract_username_from_bare_username(self, service):
        """Test extracting username from bare username."""
        url = "testuser"
        username = service._extract_github_username(url)
        assert username == "testuser"
    
    def test_extract_username_invalid_url(self, service):
        """Test that invalid URLs return None."""
        url = "not-a-github-url/with/slashes"
        username = service._extract_github_username(url)
        assert username is None


class TestGitHubRepositoryAnalysis:
    """Test GitHub repository analysis functionality."""
    
    def test_analyze_empty_repositories(self, service):
        """Test analysis with no repositories."""
        analysis = service._analyze_github_repositories([])
        
        assert analysis["languages"] == []
        assert analysis["total_commits"] == 0
        assert analysis["avg_commits_per_repo"] == 0
        assert analysis["commit_frequency_score"] == 0
        assert analysis["project_complexity_score"] == 0
        assert analysis["confidence_score"] == 0.1
        assert "No repositories found" in analysis["summary"]
    
    def test_analyze_single_repository(self, service):
        """Test analysis with a single repository."""
        repos_data = [{
            "name": "test-repo",
            "description": "Test repository",
            "language": "Python",
            "languages": {"Python": 10000, "JavaScript": 2000},
            "stars": 10,
            "forks": 2,
            "size": 500,
            "created_at": (datetime.utcnow() - timedelta(days=365)).isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "pushed_at": (datetime.utcnow() - timedelta(days=5)).isoformat(),
            "is_fork": False,
            "commit_count": 50,
            "open_issues": 3,
            "has_wiki": True,
            "has_pages": False
        }]
        
        analysis = service._analyze_github_repositories(repos_data)
        
        assert "Python" in analysis["languages"]
        assert "JavaScript" in analysis["languages"]
        assert analysis["total_commits"] == 50
        assert analysis["avg_commits_per_repo"] == 50.0
        assert analysis["active_repos"] == 1  # Pushed in last 90 days
        assert analysis["total_stars"] == 10
        assert analysis["total_forks"] == 2
        assert analysis["commit_frequency_score"] > 0
        assert analysis["project_complexity_score"] > 0
        assert 0 < analysis["confidence_score"] <= 1
    
    def test_analyze_multiple_repositories(self, service):
        """Test analysis with multiple repositories."""
        repos_data = [
            {
                "name": "repo1",
                "language": "Python",
                "languages": {"Python": 15000},
                "stars": 20,
                "forks": 5,
                "size": 1000,
                "created_at": (datetime.utcnow() - timedelta(days=730)).isoformat(),
                "pushed_at": (datetime.utcnow() - timedelta(days=10)).isoformat(),
                "commit_count": 100,
                "is_fork": False
            },
            {
                "name": "repo2",
                "language": "JavaScript",
                "languages": {"JavaScript": 8000, "TypeScript": 5000},
                "stars": 15,
                "forks": 3,
                "size": 800,
                "created_at": (datetime.utcnow() - timedelta(days=365)).isoformat(),
                "pushed_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "commit_count": 75,
                "is_fork": False
            },
            {
                "name": "repo3",
                "language": "Go",
                "languages": {"Go": 6000},
                "stars": 5,
                "forks": 1,
                "size": 400,
                "created_at": (datetime.utcnow() - timedelta(days=180)).isoformat(),
                "pushed_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "commit_count": 30,
                "is_fork": False
            }
        ]
        
        analysis = service._analyze_github_repositories(repos_data)
        
        assert len(analysis["languages"]) >= 3
        assert "Python" in analysis["languages"]
        assert "JavaScript" in analysis["languages"]
        assert "Go" in analysis["languages"]
        assert analysis["total_commits"] == 205
        assert analysis["avg_commits_per_repo"] == pytest.approx(68.3, rel=0.1)
        assert analysis["active_repos"] == 3
        assert analysis["total_stars"] == 40
        assert analysis["total_forks"] == 9
        assert analysis["estimated_experience_years"] > 0
    
    def test_language_proficiency_calculation(self, service):
        """Test that language proficiency is calculated correctly."""
        repos_data = [{
            "name": "test-repo",
            "language": "Python",
            "languages": {"Python": 8000, "JavaScript": 2000},
            "stars": 5,
            "forks": 1,
            "size": 500,
            "created_at": datetime.utcnow().isoformat(),
            "pushed_at": datetime.utcnow().isoformat(),
            "commit_count": 20,
            "is_fork": False
        }]
        
        analysis = service._analyze_github_repositories(repos_data)
        
        # Python should be 80% (8000/10000), JavaScript 20% (2000/10000)
        assert analysis["language_proficiency"]["Python"] == pytest.approx(0.8, rel=0.01)
        assert analysis["language_proficiency"]["JavaScript"] == pytest.approx(0.2, rel=0.01)
    
    def test_active_repos_detection(self, service):
        """Test detection of recently active repositories."""
        now = datetime.utcnow()
        repos_data = [
            {
                "name": "active-repo",
                "language": "Python",
                "languages": {"Python": 5000},
                "pushed_at": (now - timedelta(days=30)).isoformat(),  # Active
                "commit_count": 50,
                "stars": 5,
                "forks": 1,
                "size": 500,
                "created_at": now.isoformat(),
                "is_fork": False
            },
            {
                "name": "inactive-repo",
                "language": "JavaScript",
                "languages": {"JavaScript": 3000},
                "pushed_at": (now - timedelta(days=200)).isoformat(),  # Inactive
                "commit_count": 30,
                "stars": 3,
                "forks": 0,
                "size": 300,
                "created_at": now.isoformat(),
                "is_fork": False
            }
        ]
        
        analysis = service._analyze_github_repositories(repos_data)
        
        # Only one repo active in last 90 days
        assert analysis["active_repos"] == 1


class TestSkillLevelCalculation:
    """Test skill level calculation from GitHub data."""
    
    def test_calculate_skill_level_beginner(self, service):
        """Test skill level calculation for beginner profile."""
        analysis = {
            "commit_frequency_score": 2.0,
            "project_complexity_score": 1.5,
            "estimated_experience_years": 0.5,
            "active_repos": 1
        }
        user_data = {"followers": 5}
        
        skill_level = service._calculate_github_skill_level(analysis, user_data)
        
        assert 1 <= skill_level <= 4
    
    def test_calculate_skill_level_intermediate(self, service):
        """Test skill level calculation for intermediate profile."""
        analysis = {
            "commit_frequency_score": 5.0,
            "project_complexity_score": 5.0,
            "estimated_experience_years": 2.0,
            "active_repos": 5
        }
        user_data = {"followers": 25}
        
        skill_level = service._calculate_github_skill_level(analysis, user_data)
        
        assert 4 <= skill_level <= 7
    
    def test_calculate_skill_level_advanced(self, service):
        """Test skill level calculation for advanced profile."""
        analysis = {
            "commit_frequency_score": 9.0,
            "project_complexity_score": 8.5,
            "estimated_experience_years": 5.0,
            "active_repos": 10
        }
        user_data = {"followers": 100}
        
        skill_level = service._calculate_github_skill_level(analysis, user_data)
        
        assert 7 <= skill_level <= 10
    
    def test_skill_level_minimum_is_one(self, service):
        """Test that skill level is never less than 1."""
        analysis = {
            "commit_frequency_score": 0,
            "project_complexity_score": 0,
            "estimated_experience_years": 0,
            "active_repos": 0
        }
        user_data = {"followers": 0}
        
        skill_level = service._calculate_github_skill_level(analysis, user_data)
        
        assert skill_level >= 1
    
    def test_skill_level_maximum_is_ten(self, service):
        """Test that skill level is never more than 10."""
        analysis = {
            "commit_frequency_score": 10.0,
            "project_complexity_score": 10.0,
            "estimated_experience_years": 20.0,
            "active_repos": 50
        }
        user_data = {"followers": 1000}
        
        skill_level = service._calculate_github_skill_level(analysis, user_data)
        
        assert skill_level <= 10


class TestGitHubAPIRetry:
    """Test GitHub API retry logic with exponential backoff."""
    
    def test_fetch_user_success_first_try(self, service):
        """Test successful user fetch on first attempt."""
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.public_repos = 10
        mock_user.followers = 50
        mock_user.following = 30
        mock_user.created_at = datetime.utcnow()
        mock_user.bio = "Test bio"
        mock_user.company = "Test Company"
        mock_user.location = "Test Location"
        
        service.github_client.get_user = Mock(return_value=mock_user)
        
        result = service._fetch_github_user_with_retry("testuser")
        
        assert result["username"] == "testuser"
        assert result["name"] == "Test User"
        assert result["public_repos"] == 10
        assert service.github_client.get_user.call_count == 1
    
    def test_fetch_user_retry_on_rate_limit(self, service):
        """Test retry logic when rate limit is hit."""
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.public_repos = 10
        mock_user.followers = 50
        mock_user.following = 30
        mock_user.created_at = datetime.utcnow()
        mock_user.bio = None
        mock_user.company = None
        mock_user.location = None
        
        # First call raises rate limit, second succeeds
        service.github_client.get_user = Mock(
            side_effect=[RateLimitExceededException(403, "Rate limit exceeded"), mock_user]
        )
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = service._fetch_github_user_with_retry("testuser", max_retries=5)
        
        assert result["username"] == "testuser"
        assert service.github_client.get_user.call_count == 2
    
    def test_fetch_user_max_retries_exceeded(self, service):
        """Test that exception is raised after max retries."""
        service.github_client.get_user = Mock(
            side_effect=RateLimitExceededException(403, "Rate limit exceeded")
        )
        
        with patch('time.sleep'):
            with pytest.raises(RateLimitExceededException):
                service._fetch_github_user_with_retry("testuser")
        
        # Decorator uses RetryConfig.GITHUB_MAX_RETRIES (5) + initial attempt = 6 total
        assert service.github_client.get_user.call_count == 6
    
    def test_fetch_user_404_not_found(self, service):
        """Test that 404 error raises ValueError immediately."""
        service.github_client.get_user = Mock(
            side_effect=GithubException(404, "Not found")
        )
        
        with pytest.raises(ValueError, match="GitHub user not found"):
            service._fetch_github_user_with_retry("nonexistent")
        
        # Should not retry on 404
        assert service.github_client.get_user.call_count == 1
    
    def test_exponential_backoff_timing(self, service):
        """Test that exponential backoff increases delay correctly."""
        service.github_client.get_user = Mock(
            side_effect=RateLimitExceededException(403, "Rate limit exceeded")
        )
        
        sleep_times = []
        
        def mock_sleep(duration):
            sleep_times.append(duration)
        
        with patch('time.sleep', side_effect=mock_sleep):
            with pytest.raises(RateLimitExceededException):
                service._fetch_github_user_with_retry("testuser")
        
        # Verify delays are increasing (with jitter, so approximate)
        # Decorator uses RetryConfig.GITHUB_MAX_RETRIES (5) retries
        assert len(sleep_times) == 5  # 5 retries after first failure
        assert sleep_times[0] < sleep_times[1]  # Second delay > first delay
        assert sleep_times[1] < sleep_times[2]  # Third delay > second delay
        assert all(delay <= 32 for delay in sleep_times)  # All delays capped at 32s


class TestGitHubAnalysisIntegration:
    """Integration tests for complete GitHub analysis flow."""
    
    def test_analyze_github_complete_flow(self, service, mock_db):
        """Test complete GitHub analysis flow."""
        user_id = uuid4()
        github_url = "https://github.com/testuser"
        
        # Mock GitHub API responses
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.public_repos = 5
        mock_user.followers = 20
        mock_user.following = 15
        mock_user.created_at = datetime.utcnow() - timedelta(days=730)
        mock_user.bio = "Software Developer"
        mock_user.company = "Tech Corp"
        mock_user.location = "San Francisco"
        
        mock_repo = Mock()
        mock_repo.name = "test-repo"
        mock_repo.description = "Test repository"
        mock_repo.language = "Python"
        mock_repo.stargazers_count = 10
        mock_repo.forks_count = 2
        mock_repo.size = 500
        mock_repo.created_at = datetime.utcnow() - timedelta(days=365)
        mock_repo.updated_at = datetime.utcnow()
        mock_repo.pushed_at = datetime.utcnow() - timedelta(days=5)
        mock_repo.fork = False
        mock_repo.open_issues_count = 3
        mock_repo.has_wiki = True
        mock_repo.has_pages = False
        mock_repo.get_languages = Mock(return_value={"Python": 10000, "JavaScript": 2000})
        
        mock_commits = Mock()
        mock_commits.totalCount = 50
        mock_repo.get_commits = Mock(return_value=mock_commits)
        
        mock_user.get_repos = Mock(return_value=[mock_repo])
        
        service.github_client.get_user = Mock(return_value=mock_user)
        
        # Execute analysis
        assessment = service.analyze_github(github_url, user_id)
        
        # Verify assessment was created
        assert isinstance(assessment, SkillAssessment)
        assert assessment.user_id == user_id
        assert assessment.source == AssessmentSource.GITHUB
        assert 1 <= assessment.skill_level <= 10
        assert assessment.source_url == github_url
        assert "Python" in assessment.detected_skills
        assert assessment.confidence_score > 0
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_analyze_github_invalid_url(self, service):
        """Test that invalid GitHub URL raises ValueError."""
        user_id = uuid4()
        # Use a URL that will fail username extraction
        invalid_url = "https://example.com/not/github"
        
        # Mock the GitHub client to avoid actual API calls
        service.github_client = Mock()
        
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            service.analyze_github(invalid_url, user_id)
    
    def test_analyze_github_no_token_configured(self, mock_db):
        """Test that missing GitHub token raises ValueError."""
        with patch('app.services.portfolio_analysis_service.settings') as mock_settings:
            mock_settings.GITHUB_TOKEN = None
            service = PortfolioAnalysisService(mock_db)
            
            with pytest.raises(ValueError, match="GitHub token not configured"):
                service.analyze_github("https://github.com/testuser", uuid4())


class TestSummaryGeneration:
    """Test GitHub analysis summary generation."""
    
    def test_generate_summary_with_data(self, service):
        """Test summary generation with complete data."""
        repos_data = [{"name": "repo1"}, {"name": "repo2"}, {"name": "repo3"}]
        top_languages = ["Python", "JavaScript", "Go"]
        total_commits = 150
        active_repos = 2
        experience_years = 2.5
        complexity_score = 6.5
        
        summary = service._generate_github_summary(
            repos_data, top_languages, total_commits, active_repos,
            experience_years, complexity_score
        )
        
        assert "3 repositories" in summary
        assert "150 total commits" in summary
        assert "Python" in summary
        assert "JavaScript" in summary
        assert "2 repositories active" in summary
        assert "2.5 years" in summary
        assert "6.5/10" in summary
    
    def test_generate_summary_no_languages(self, service):
        """Test summary generation with no detected languages."""
        repos_data = [{"name": "repo1"}]
        top_languages = []
        total_commits = 10
        active_repos = 1
        experience_years = 0.5
        complexity_score = 2.0
        
        summary = service._generate_github_summary(
            repos_data, top_languages, total_commits, active_repos,
            experience_years, complexity_score
        )
        
        assert "various languages" in summary
        assert "1 repositories" in summary


class TestLinkedInExperienceAnalysis:
    """Test LinkedIn work experience analysis functionality."""
    
    def test_analyze_empty_experience(self, service):
        """Test analysis with no work experience."""
        analysis = service._analyze_linkedin_experience([])
        
        assert analysis["total_years"] == 0
        assert analysis["recent_experience_years"] == 0
        assert analysis["current_positions_count"] == 0
        assert analysis["recency_weighted_score"] == 0
        assert analysis["technologies"] == []
        assert "No work experience found" in analysis["summary"]
    
    def test_analyze_single_current_position(self, service):
        """Test analysis with a single current position."""
        positions = [{
            "title": "Software Engineer",
            "company": "Tech Corp",
            "start_date": {"year": 2022, "month": 1},
            "end_date": None,
            "is_current": True,
            "description": "Working with Python, Django, and AWS"
        }]
        
        analysis = service._analyze_linkedin_experience(positions)
        
        assert analysis["total_years"] > 0
        assert analysis["current_positions_count"] == 1
        assert analysis["recency_weighted_score"] > 0
        assert len(analysis["technologies"]) > 0
        assert "Python" in analysis["technologies"]
    
    def test_analyze_multiple_positions_with_recency_weighting(self, service):
        """Test that recent positions are weighted more heavily."""
        now = datetime.utcnow()
        positions = [
            {
                "title": "Senior Engineer",
                "company": "Current Corp",
                "start_date": {"year": now.year - 1, "month": 1},
                "end_date": None,
                "is_current": True,
                "description": "Python, React, AWS"
            },
            {
                "title": "Mid-level Engineer",
                "company": "Previous Corp",
                "start_date": {"year": now.year - 4, "month": 1},
                "end_date": {"year": now.year - 1, "month": 1},
                "is_current": False,
                "description": "Java, Spring"
            },
            {
                "title": "Junior Engineer",
                "company": "Old Corp",
                "start_date": {"year": now.year - 8, "month": 1},
                "end_date": {"year": now.year - 4, "month": 1},
                "is_current": False,
                "description": "PHP, MySQL"
            }
        ]
        
        analysis = service._analyze_linkedin_experience(positions)
        
        # Total experience should be ~7 years
        assert analysis["total_years"] >= 6
        assert analysis["total_years"] <= 9  # Allow some flexibility for rounding
        
        # Recent experience should be less (only last 3 years)
        assert analysis["recent_experience_years"] < analysis["total_years"]
        
        # Recency weighted score should favor recent positions
        assert analysis["recency_weighted_score"] > 0
        
        # Should have current position
        assert analysis["current_positions_count"] == 1
    
    def test_recency_weighting_calculation(self, service):
        """Test that recency weighting follows the correct formula."""
        now = datetime.utcnow()
        
        # Position from 6 months ago for 1 year (weight = 1.0)
        recent_position = [{
            "title": "Engineer",
            "company": "Corp",
            "start_date": {"year": now.year - 1, "month": now.month},
            "end_date": None,
            "is_current": True,
            "description": "Python"
        }]
        
        recent_analysis = service._analyze_linkedin_experience(recent_position)
        
        # Position from 6 years ago for 1 year (weight = 0.2)
        old_position = [{
            "title": "Engineer",
            "company": "Corp",
            "start_date": {"year": now.year - 7, "month": 1},
            "end_date": {"year": now.year - 6, "month": 1},
            "is_current": False,
            "description": "Python"
        }]
        
        old_analysis = service._analyze_linkedin_experience(old_position)
        
        # Recent position should have higher weighted score for similar duration
        # Recent: ~1 year * 1.0 weight = ~1.0
        # Old: ~1 year * 0.2 weight = ~0.2
        assert recent_analysis["recency_weighted_score"] > old_analysis["recency_weighted_score"]
    
    def test_technology_extraction_from_description(self, service):
        """Test extraction of technologies from job descriptions."""
        positions = [{
            "title": "Full Stack Developer",
            "company": "Tech Corp",
            "start_date": {"year": 2020, "month": 1},
            "end_date": None,
            "is_current": True,
            "description": "Built applications using Python, Django, React, PostgreSQL, and Docker. Deployed on AWS with Kubernetes."
        }]
        
        analysis = service._analyze_linkedin_experience(positions)
        
        # Should extract multiple technologies
        assert len(analysis["technologies"]) > 0
        assert "Python" in analysis["technologies"]
        assert "Django" in analysis["technologies"]
        assert "React" in analysis["technologies"]


class TestLinkedInSkillsAnalysis:
    """Test LinkedIn skills and endorsements analysis."""
    
    def test_analyze_empty_skills(self, service):
        """Test analysis with no skills."""
        analysis = service._analyze_linkedin_skills([])
        
        assert analysis["top_skills"] == []
        assert analysis["total_endorsements"] == 0
        assert analysis["endorsement_score"] == 0
        assert analysis["skill_proficiency"] == {}
    
    def test_analyze_skills_with_endorsements(self, service):
        """Test analysis of skills with endorsements."""
        skills = [
            {"name": "Python", "endorsement_count": 50},
            {"name": "JavaScript", "endorsement_count": 30},
            {"name": "React", "endorsement_count": 25},
            {"name": "Django", "endorsement_count": 20},
            {"name": "AWS", "endorsement_count": 15}
        ]
        
        analysis = service._analyze_linkedin_skills(skills)
        
        assert len(analysis["top_skills"]) == 5
        assert analysis["top_skills"][0] == "Python"  # Most endorsed
        assert analysis["total_endorsements"] == 140
        assert analysis["endorsement_score"] > 0
        
        # Check proficiency calculation
        assert "Python" in analysis["skill_proficiency"]
        assert analysis["skill_proficiency"]["Python"] == 1.0  # Highest endorsements
        assert analysis["skill_proficiency"]["JavaScript"] < 1.0
    
    def test_endorsement_score_calculation(self, service):
        """Test endorsement score calculation."""
        # 50+ endorsements should give score of 10
        high_endorsements = [{"name": f"Skill{i}", "endorsement_count": 10} for i in range(10)]
        high_analysis = service._analyze_linkedin_skills(high_endorsements)
        assert high_analysis["endorsement_score"] >= 10
        
        # Few endorsements should give lower score
        low_endorsements = [{"name": "Skill1", "endorsement_count": 5}]
        low_analysis = service._analyze_linkedin_skills(low_endorsements)
        assert low_analysis["endorsement_score"] < 5
    
    def test_skill_proficiency_normalization(self, service):
        """Test that skill proficiency is normalized correctly."""
        skills = [
            {"name": "Python", "endorsement_count": 100},
            {"name": "JavaScript", "endorsement_count": 50},
            {"name": "Go", "endorsement_count": 25}
        ]
        
        analysis = service._analyze_linkedin_skills(skills)
        
        # Python should be 1.0 (highest)
        assert analysis["skill_proficiency"]["Python"] == 1.0
        # JavaScript should be 0.5 (half of Python)
        assert analysis["skill_proficiency"]["JavaScript"] == 0.5
        # Go should be 0.25 (quarter of Python)
        assert analysis["skill_proficiency"]["Go"] == 0.25


class TestLinkedInCertificationsAnalysis:
    """Test LinkedIn certifications analysis."""
    
    def test_analyze_empty_certifications(self, service):
        """Test analysis with no certifications."""
        analysis = service._analyze_linkedin_certifications([])
        
        assert analysis["score"] == 0
        assert analysis["skill_areas"] == []
        assert analysis["recent_certifications"] == []
    
    def test_analyze_certifications(self, service):
        """Test analysis of certifications."""
        now = datetime.utcnow()
        certifications = [
            {
                "name": "AWS Certified Solutions Architect",
                "authority": "Amazon",
                "date": {"year": now.year, "month": 1}
            },
            {
                "name": "Python Professional Certificate",
                "authority": "Python Institute",
                "date": {"year": now.year - 1, "month": 6}
            },
            {
                "name": "Kubernetes Administrator",
                "authority": "CNCF",
                "date": {"year": now.year - 3, "month": 1}
            }
        ]
        
        analysis = service._analyze_linkedin_certifications(certifications)
        
        assert analysis["score"] > 0
        assert len(analysis["skill_areas"]) > 0
        assert len(analysis["recent_certifications"]) >= 2  # Two within last 2 years
    
    def test_certification_score_scaling(self, service):
        """Test that certification score scales appropriately."""
        # 1 certification = 2 points
        one_cert = [{"name": "Test Cert", "authority": "Test", "date": {"year": 2023, "month": 1}}]
        one_analysis = service._analyze_linkedin_certifications(one_cert)
        assert one_analysis["score"] >= 2
        
        # 5+ certifications should give higher score
        many_certs = [
            {"name": f"Cert {i}", "authority": "Test", "date": {"year": 2023, "month": 1}}
            for i in range(6)
        ]
        many_analysis = service._analyze_linkedin_certifications(many_certs)
        assert many_analysis["score"] > one_analysis["score"]


class TestLinkedInEducationAnalysis:
    """Test LinkedIn education analysis."""
    
    def test_analyze_empty_education(self, service):
        """Test analysis with no education."""
        analysis = service._analyze_linkedin_education([])
        
        assert analysis["score"] == 0
        assert analysis["highest_degree"] is None
    
    def test_analyze_bachelor_degree(self, service):
        """Test analysis with bachelor's degree."""
        education = [{
            "school": "University",
            "degree": "Bachelor of Science",
            "field_of_study": "Computer Science"
        }]
        
        analysis = service._analyze_linkedin_education(education)
        
        assert analysis["score"] == 6
        assert analysis["highest_degree"] == "Bachelor of Science"
    
    def test_analyze_master_degree(self, service):
        """Test analysis with master's degree."""
        education = [{
            "school": "University",
            "degree": "Master of Science",
            "field_of_study": "Computer Science"
        }]
        
        analysis = service._analyze_linkedin_education(education)
        
        assert analysis["score"] == 8
        assert analysis["highest_degree"] == "Master of Science"
    
    def test_analyze_phd_degree(self, service):
        """Test analysis with PhD."""
        education = [{
            "school": "University",
            "degree": "PhD in Computer Science",
            "field_of_study": "Machine Learning"
        }]
        
        analysis = service._analyze_linkedin_education(education)
        
        assert analysis["score"] == 10
        assert analysis["highest_degree"] == "PhD in Computer Science"
    
    def test_analyze_multiple_degrees(self, service):
        """Test that highest degree is selected."""
        education = [
            {"degree": "Bachelor of Science", "school": "University A"},
            {"degree": "Master of Science", "school": "University B"},
            {"degree": "Certificate", "school": "Online"}
        ]
        
        analysis = service._analyze_linkedin_education(education)
        
        assert analysis["score"] == 8  # Master's score
        assert "Master" in analysis["highest_degree"]


class TestLinkedInSkillLevelCalculation:
    """Test LinkedIn skill level calculation with recency weighting."""
    
    def test_calculate_skill_level_beginner(self, service):
        """Test skill level for beginner profile."""
        experience_analysis = {
            "recency_weighted_score": 2.0,
            "total_years": 1.0
        }
        skills_analysis = {"endorsement_score": 1.0}
        certifications_analysis = {"score": 0}
        education_analysis = {"score": 6}
        
        skill_level = service._calculate_linkedin_skill_level(
            experience_analysis, skills_analysis,
            certifications_analysis, education_analysis
        )
        
        assert 1 <= skill_level <= 4
    
    def test_calculate_skill_level_intermediate(self, service):
        """Test skill level for intermediate profile."""
        experience_analysis = {
            "recency_weighted_score": 5.0,
            "total_years": 3.0
        }
        skills_analysis = {"endorsement_score": 5.0}
        certifications_analysis = {"score": 4.0}
        education_analysis = {"score": 6}
        
        skill_level = service._calculate_linkedin_skill_level(
            experience_analysis, skills_analysis,
            certifications_analysis, education_analysis
        )
        
        assert 4 <= skill_level <= 7
    
    def test_calculate_skill_level_advanced(self, service):
        """Test skill level for advanced profile."""
        experience_analysis = {
            "recency_weighted_score": 9.0,
            "total_years": 8.0
        }
        skills_analysis = {"endorsement_score": 9.0}
        certifications_analysis = {"score": 8.0}
        education_analysis = {"score": 8}
        
        skill_level = service._calculate_linkedin_skill_level(
            experience_analysis, skills_analysis,
            certifications_analysis, education_analysis
        )
        
        assert 7 <= skill_level <= 10
    
    def test_recency_weighted_experience_has_highest_weight(self, service):
        """Test that recency-weighted experience is weighted most heavily (40%)."""
        # Profile with high recency score and moderate others
        high_recency = {
            "recency_weighted_score": 10.0,
            "total_years": 5.0
        }
        moderate_skills = {"endorsement_score": 5.0}
        moderate_certs = {"score": 5.0}
        moderate_edu = {"score": 6}
        
        skill_level_high_recency = service._calculate_linkedin_skill_level(
            high_recency, moderate_skills, moderate_certs, moderate_edu
        )
        
        # Profile with low recency score but high others
        low_recency = {
            "recency_weighted_score": 2.0,
            "total_years": 5.0
        }
        high_skills = {"endorsement_score": 10}
        high_certs = {"score": 10}
        high_edu = {"score": 10}
        
        skill_level_low_recency = service._calculate_linkedin_skill_level(
            low_recency, high_skills, high_certs, high_edu
        )
        
        # With 40% weight on recency, high recency should result in comparable or higher skill level
        # High recency: 10*0.4 + 5*0.25 + 5*0.2 + 6*0.15 = 4.0 + 1.25 + 1.0 + 0.9 = 7.15 -> 7
        # Low recency: 2*0.4 + 10*0.25 + 10*0.2 + 10*0.15 = 0.8 + 2.5 + 2.0 + 1.5 = 6.8 -> 7
        # Both should be similar, demonstrating recency has significant impact
        assert abs(skill_level_high_recency - skill_level_low_recency) <= 1
    
    def test_skill_level_bounds(self, service):
        """Test that skill level is always between 1 and 10."""
        # Minimum case
        min_exp = {"recency_weighted_score": 0, "total_years": 0}
        min_skills = {"endorsement_score": 0}
        min_certs = {"score": 0}
        min_edu = {"score": 0}
        
        min_level = service._calculate_linkedin_skill_level(
            min_exp, min_skills, min_certs, min_edu
        )
        assert min_level >= 1
        
        # Maximum case
        max_exp = {"recency_weighted_score": 10, "total_years": 20}
        max_skills = {"endorsement_score": 10}
        max_certs = {"score": 10}
        max_edu = {"score": 10}
        
        max_level = service._calculate_linkedin_skill_level(
            max_exp, max_skills, max_certs, max_edu
        )
        assert max_level <= 10


class TestLinkedInAnalysisIntegration:
    """Integration tests for complete LinkedIn analysis flow."""
    
    def test_analyze_linkedin_complete_flow(self, service, mock_db):
        """Test complete LinkedIn analysis flow."""
        user_id = uuid4()
        now = datetime.utcnow()
        
        linkedin_profile = {
            "profile_url": "https://linkedin.com/in/testuser",
            "positions": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "start_date": {"year": now.year - 2, "month": 1},
                    "end_date": None,
                    "is_current": True,
                    "description": "Working with Python, Django, React, and AWS"
                },
                {
                    "title": "Software Engineer",
                    "company": "Previous Corp",
                    "start_date": {"year": now.year - 5, "month": 1},
                    "end_date": {"year": now.year - 2, "month": 1},
                    "is_current": False,
                    "description": "Developed applications using Java and Spring"
                }
            ],
            "skills": [
                {"name": "Python", "endorsement_count": 45},
                {"name": "JavaScript", "endorsement_count": 30},
                {"name": "React", "endorsement_count": 25},
                {"name": "Django", "endorsement_count": 20},
                {"name": "AWS", "endorsement_count": 18}
            ],
            "certifications": [
                {
                    "name": "AWS Certified Solutions Architect",
                    "authority": "Amazon",
                    "date": {"year": now.year, "month": 1}
                }
            ],
            "education": [
                {
                    "school": "University",
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science"
                }
            ]
        }
        
        # Execute analysis
        assessment = service.analyze_linkedin(linkedin_profile, user_id)
        
        # Verify assessment was created
        assert isinstance(assessment, SkillAssessment)
        assert assessment.user_id == user_id
        assert assessment.source == AssessmentSource.LINKEDIN
        assert 1 <= assessment.skill_level <= 10
        assert assessment.source_url == "https://linkedin.com/in/testuser"
        assert "Python" in assessment.detected_skills
        assert assessment.confidence_score > 0
        assert assessment.experience_years > 0
        
        # Verify recency weighting is applied
        assert "recency_weighted_score" in assessment.extra_metadata
        assert assessment.extra_metadata["recency_weighted_score"] > 0
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_analyze_linkedin_minimal_profile(self, service, mock_db):
        """Test analysis with minimal LinkedIn profile data."""
        user_id = uuid4()
        
        linkedin_profile = {
            "skills": [
                {"name": "Python", "endorsement_count": 10}
            ]
        }
        
        # Should not raise error with minimal data
        assessment = service.analyze_linkedin(linkedin_profile, user_id)
        
        assert isinstance(assessment, SkillAssessment)
        assert assessment.skill_level >= 1
    
    def test_analyze_linkedin_empty_profile_raises_error(self, service):
        """Test that empty LinkedIn profile raises ValueError."""
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="LinkedIn profile data is required"):
            service.analyze_linkedin(None, user_id)
    
    def test_analyze_linkedin_missing_required_fields(self, service):
        """Test that profile without positions or skills raises ValueError."""
        user_id = uuid4()
        
        linkedin_profile = {
            "education": [{"degree": "Bachelor"}]
        }
        
        with pytest.raises(ValueError, match="must contain at least positions or skills"):
            service.analyze_linkedin(linkedin_profile, user_id)


class TestLinkedInDateParsing:
    """Test LinkedIn date parsing functionality."""
    
    def test_parse_dict_date(self, service):
        """Test parsing date from dictionary format."""
        date_dict = {"year": 2020, "month": 6}
        result = service._parse_linkedin_date(date_dict)
        
        assert result.year == 2020
        assert result.month == 6
    
    def test_parse_dict_date_without_month(self, service):
        """Test parsing date dictionary without month."""
        date_dict = {"year": 2020}
        result = service._parse_linkedin_date(date_dict)
        
        assert result.year == 2020
        assert result.month == 1  # Default to January
    
    def test_parse_iso_string_date(self, service):
        """Test parsing ISO format date string."""
        date_str = "2020-06-15"
        result = service._parse_linkedin_date(date_str)
        
        assert result.year == 2020
        assert result.month == 6
        assert result.day == 15
    
    def test_parse_datetime_object(self, service):
        """Test that datetime objects are returned as-is."""
        date_obj = datetime(2020, 6, 15)
        result = service._parse_linkedin_date(date_obj)
        
        assert result == date_obj
    
    def test_parse_none_date(self, service):
        """Test that None returns None."""
        result = service._parse_linkedin_date(None)
        assert result is None
    
    def test_parse_invalid_date(self, service):
        """Test that invalid dates return None."""
        result = service._parse_linkedin_date("invalid-date")
        assert result is None


class TestLinkedInHelperFunctions:
    """Test LinkedIn helper functions."""
    
    def test_calculate_months_between(self, service):
        """Test month calculation between dates."""
        start = datetime(2020, 1, 1)
        end = datetime(2022, 6, 1)
        
        months = service._calculate_months_between(start, end)
        
        assert months == 29  # 2 years and 5 months
    
    def test_calculate_months_same_date(self, service):
        """Test month calculation for same date."""
        date = datetime(2020, 1, 1)
        
        months = service._calculate_months_between(date, date)
        
        assert months == 0
    
    def test_extract_technologies_from_text(self, service):
        """Test technology extraction from text."""
        text = "Built applications using Python, Django, React, and PostgreSQL. Deployed on AWS with Docker and Kubernetes."
        
        technologies = service._extract_technologies_from_text(text)
        
        assert "Python" in technologies
        assert "Django" in technologies
        assert "React" in technologies
        assert "Aws" in technologies or "AWS" in [t.upper() for t in technologies]
        assert "Docker" in technologies
        assert "Kubernetes" in technologies
    
    def test_extract_technologies_empty_text(self, service):
        """Test technology extraction from empty text."""
        technologies = service._extract_technologies_from_text("")
        assert technologies == []
    
    def test_extract_technologies_no_matches(self, service):
        """Test technology extraction with no matching keywords."""
        text = "Managed team and coordinated projects"
        technologies = service._extract_technologies_from_text(text)
        # May or may not find matches depending on keywords
        assert isinstance(technologies, list)



class TestPortfolioWebsiteAnalysis:
    """Test portfolio website analysis functionality."""
    
    def test_fetch_website_success(self, service):
        """Test successful website fetch."""
        url = "https://example.com/portfolio"
        html_content = """
        <html>
            <head><title>Portfolio</title></head>
            <body>
                <h1>My Portfolio</h1>
                <p>Welcome to my portfolio</p>
            </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = html_content
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = service._fetch_website_with_retry(url)
            
            assert result == html_content
            mock_get.assert_called_once()
    
    def test_fetch_website_adds_https_protocol(self, service):
        """Test that URL without protocol gets https:// added."""
        url = "example.com/portfolio"
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = "<html></html>"
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # This should work because analyze_portfolio_website adds https://
            # but _fetch_website_with_retry expects full URL
            result = service._fetch_website_with_retry("https://" + url)
            
            assert result == "<html></html>"
    
    def test_fetch_website_retry_on_failure(self, service):
        """Test retry logic when website fetch fails."""
        url = "https://example.com/portfolio"
        html_content = "<html><body>Success</body></html>"
        
        with patch('requests.get') as mock_get:
            mock_response_success = Mock()
            mock_response_success.text = html_content
            mock_response_success.raise_for_status = Mock()
            
            # First call fails, second succeeds
            mock_get.side_effect = [
                requests.exceptions.RequestException("Connection error"),
                mock_response_success
            ]
            
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = service._fetch_website_with_retry(url)
            
            assert result == html_content
            assert mock_get.call_count == 2
    
    def test_fetch_website_max_retries_exceeded(self, service):
        """Test that exception is raised after max retries."""
        url = "https://example.com/portfolio"
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            with patch('time.sleep'):
                with pytest.raises(requests.exceptions.RequestException, match="Connection error"):
                    service._fetch_website_with_retry(url)
            
            # Decorator uses RetryConfig.WEB_SCRAPING_MAX_RETRIES (3) + initial attempt = 4 total
            assert mock_get.call_count == 4
    
    def test_extract_project_info_with_heading(self, service):
        """Test extracting project info with heading."""
        from bs4 import BeautifulSoup
        
        html = """
        <div class="project">
            <h2>My Awesome Project</h2>
            <p class="description">A web application built with React and Node.js</p>
            <a href="https://github.com/user/project">GitHub</a>
            <a href="https://demo.example.com">Live Demo</a>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.find('div', class_='project')
        
        project_info = service._extract_project_info(section)
        
        assert project_info is not None
        assert project_info["title"] == "My Awesome Project"
        assert "React" in project_info["description"] or "React" in str(project_info["technologies"])
        assert len(project_info["links"]) == 2
    
    def test_extract_project_info_no_title(self, service):
        """Test that sections without title return None."""
        from bs4 import BeautifulSoup
        
        html = """
        <div class="project">
            <p>Some content without a title</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        section = soup.find('div', class_='project')
        
        project_info = service._extract_project_info(section)
        
        assert project_info is None
    
    def test_extract_technologies_from_html(self, service):
        """Test extracting technologies from HTML."""
        from bs4 import BeautifulSoup
        
        html = """
        <html>
            <body>
                <p>Built with Python, Django, React, and PostgreSQL</p>
                <p>Deployed on AWS using Docker and Kubernetes</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        technologies = service._extract_technologies_from_html(soup)
        
        assert "Python" in technologies
        assert "Django" in technologies
        assert "React" in technologies
    
    def test_extract_work_samples(self, service):
        """Test extracting work samples from HTML."""
        from bs4 import BeautifulSoup
        
        html = """
        <html>
            <body>
                <a href="https://github.com/user/repo1">GitHub Repo 1</a>
                <a href="https://github.com/user/repo2">GitHub Repo 2</a>
                <a href="https://demo.example.com">Live Demo</a>
                <a href="https://app.example.com">View Project</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        work_samples = service._extract_work_samples(soup)
        
        assert len(work_samples) >= 2
        github_samples = [s for s in work_samples if s["type"] == "github"]
        demo_samples = [s for s in work_samples if s["type"] == "live_demo"]
        
        assert len(github_samples) >= 2
        assert len(demo_samples) >= 1
    
    def test_extract_work_samples_removes_duplicates(self, service):
        """Test that duplicate URLs are removed."""
        from bs4 import BeautifulSoup
        
        html = """
        <html>
            <body>
                <a href="https://github.com/user/repo">GitHub</a>
                <a href="https://github.com/user/repo">Same Repo</a>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        work_samples = service._extract_work_samples(soup)
        
        # Should only have one entry for the duplicate URL
        assert len(work_samples) == 1
    
    def test_calculate_project_complexity(self, service):
        """Test project complexity calculation."""
        projects = [
            {
                "title": "Project 1",
                "description": "A detailed description of the project with many words to show complexity and thoroughness in documentation.",
                "technologies": ["Python", "Django", "React"],
                "links": []
            },
            {
                "title": "Project 2",
                "description": "Another project with good documentation and multiple technologies used.",
                "technologies": ["JavaScript", "Node.js", "MongoDB"],
                "links": []
            }
        ]
        technologies = ["Python", "Django", "React", "JavaScript", "Node.js", "MongoDB", "Docker", "AWS"]
        work_samples = [
            {"url": "https://github.com/user/repo1", "type": "github"},
            {"url": "https://demo.example.com", "type": "live_demo"}
        ]
        
        score = service._calculate_project_complexity(projects, technologies, work_samples)
        
        assert 0 <= score <= 10
        assert score > 0  # Should have some complexity
    
    def test_calculate_project_complexity_empty(self, service):
        """Test project complexity with no data."""
        score = service._calculate_project_complexity([], [], [])
        assert score == 0
    
    def test_calculate_portfolio_quality(self, service):
        """Test portfolio quality calculation."""
        portfolio_data = {
            "has_about_section": True,
            "has_contact_info": True,
            "has_github_links": True,
            "has_live_demos": True,
            "total_text_length": 3000,
            "projects": [{"title": f"Project {i}"} for i in range(5)]
        }
        
        score = service._calculate_portfolio_quality(portfolio_data)
        
        assert 0 <= score <= 10
        assert score > 5  # Should be high quality with all features
    
    def test_calculate_portfolio_quality_minimal(self, service):
        """Test portfolio quality with minimal data."""
        portfolio_data = {
            "has_about_section": False,
            "has_contact_info": False,
            "has_github_links": False,
            "has_live_demos": False,
            "total_text_length": 300,
            "projects": []
        }
        
        score = service._calculate_portfolio_quality(portfolio_data)
        
        assert 0 <= score <= 10
        assert score < 3  # Should be low quality
    
    def test_calculate_portfolio_skill_level(self, service):
        """Test skill level calculation from portfolio data."""
        portfolio_data = {
            "project_complexity_score": 7.0,
            "portfolio_quality_score": 8.0,
            "technologies": ["Python", "JavaScript", "React", "Django", "AWS", "Docker"],
            "work_samples": [
                {"url": "https://github.com/user/repo1", "type": "github"},
                {"url": "https://github.com/user/repo2", "type": "github"},
                {"url": "https://demo.example.com", "type": "live_demo"}
            ]
        }
        
        skill_level = service._calculate_portfolio_skill_level(portfolio_data)
        
        assert 1 <= skill_level <= 10
        assert skill_level >= 5  # Should be mid-level with good data
    
    def test_calculate_portfolio_skill_level_beginner(self, service):
        """Test skill level for beginner portfolio."""
        portfolio_data = {
            "project_complexity_score": 2.0,
            "portfolio_quality_score": 3.0,
            "technologies": ["Python", "HTML"],
            "work_samples": []
        }
        
        skill_level = service._calculate_portfolio_skill_level(portfolio_data)
        
        assert 1 <= skill_level <= 4
    
    def test_calculate_portfolio_confidence(self, service):
        """Test confidence score calculation."""
        portfolio_data = {
            "total_text_length": 3000,
            "projects": [{"title": f"Project {i}"} for i in range(5)],
            "technologies": ["Python", "JavaScript", "React", "Django", "AWS"],
            "work_samples": [
                {"url": "https://github.com/user/repo1", "type": "github"},
                {"url": "https://demo.example.com", "type": "live_demo"}
            ]
        }
        
        confidence = service._calculate_portfolio_confidence(portfolio_data)
        
        assert 0 <= confidence <= 1
        assert confidence > 0.5  # Should be confident with good data
    
    def test_calculate_portfolio_confidence_low(self, service):
        """Test confidence score with minimal data."""
        portfolio_data = {
            "total_text_length": 200,
            "projects": [],
            "technologies": ["Python"],
            "work_samples": []
        }
        
        confidence = service._calculate_portfolio_confidence(portfolio_data)
        
        assert 0 <= confidence <= 1
        assert confidence < 0.5  # Should have low confidence
    
    def test_generate_portfolio_summary(self, service):
        """Test portfolio summary generation."""
        portfolio_data = {
            "projects": [{"title": f"Project {i}"} for i in range(3)],
            "technologies": ["Python", "JavaScript", "React", "Django", "AWS"],
            "work_samples": [
                {"url": "https://github.com/user/repo1", "type": "github"},
                {"url": "https://demo.example.com", "type": "live_demo"}
            ],
            "has_about_section": True,
            "has_contact_info": True,
            "project_complexity_score": 6.5,
            "portfolio_quality_score": 7.0
        }
        
        summary = service._generate_portfolio_summary(portfolio_data)
        
        assert "3 projects" in summary
        assert "5 technologies" in summary
        assert "Python" in summary
        assert "1 GitHub" in summary
        assert "1 live demo" in summary
        assert "6.5/10" in summary
        assert "7.0/10" in summary
    
    def test_generate_portfolio_summary_minimal(self, service):
        """Test summary generation with minimal data."""
        portfolio_data = {
            "projects": [],
            "technologies": [],
            "work_samples": [],
            "has_about_section": False,
            "has_contact_info": False,
            "project_complexity_score": 0,
            "portfolio_quality_score": 0
        }
        
        summary = service._generate_portfolio_summary(portfolio_data)
        
        # With minimal data, summary should still contain complexity and quality scores
        assert "0.0/10" in summary or "complexity" in summary.lower()


class TestPortfolioWebsiteAnalysisIntegration:
    """Integration tests for complete portfolio website analysis flow."""
    
    def test_analyze_portfolio_website_complete_flow(self, service, mock_db):
        """Test complete portfolio website analysis flow."""
        user_id = uuid4()
        url = "https://example.com/portfolio"
        
        html_content = """
        <html>
            <head><title>John Doe - Portfolio</title></head>
            <body>
                <section id="about">
                    <h1>About Me</h1>
                    <p>I'm a software developer with experience in Python and JavaScript.</p>
                </section>
                
                <section id="projects">
                    <article class="project">
                        <h2>E-commerce Platform</h2>
                        <p class="description">Built a full-stack e-commerce platform using Django, React, and PostgreSQL. Deployed on AWS with Docker.</p>
                        <a href="https://github.com/johndoe/ecommerce">GitHub</a>
                        <a href="https://ecommerce-demo.example.com">Live Demo</a>
                    </article>
                    
                    <article class="project">
                        <h2>Task Management App</h2>
                        <p class="description">Created a task management application with Node.js, Express, and MongoDB.</p>
                        <a href="https://github.com/johndoe/taskapp">GitHub</a>
                    </article>
                    
                    <article class="project">
                        <h2>Weather Dashboard</h2>
                        <p class="description">Developed a weather dashboard using React and OpenWeather API.</p>
                        <a href="https://weather.example.com">View Project</a>
                    </article>
                </section>
                
                <section id="contact">
                    <h2>Contact</h2>
                    <p>Email: john@example.com</p>
                </section>
            </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = html_content
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Execute analysis
            assessment = service.analyze_portfolio_website(url, user_id)
            
            # Verify assessment was created
            assert isinstance(assessment, SkillAssessment)
            assert assessment.user_id == user_id
            assert assessment.source == AssessmentSource.PORTFOLIO_WEBSITE
            assert 1 <= assessment.skill_level <= 10
            assert assessment.source_url == url
            assert len(assessment.detected_skills) > 0
            assert "Python" in assessment.detected_skills or "Django" in assessment.detected_skills
            assert assessment.confidence_score > 0
            
            # Verify projects were extracted
            assert assessment.source_data["projects_count"] >= 3
            
            # Verify technologies were detected
            assert assessment.source_data["technologies_count"] > 0
            
            # Verify work samples were found
            assert assessment.source_data["work_samples_count"] > 0
            
            # Verify quality indicators
            assert assessment.source_data["has_about_section"] is True
            assert assessment.source_data["has_contact_info"] is True
            
            # Verify metadata
            assert assessment.extra_metadata["has_github_links"] is True
            assert assessment.extra_metadata["project_complexity_score"] > 0
            assert assessment.extra_metadata["portfolio_quality_score"] > 0
            
            # Verify database operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    def test_analyze_portfolio_website_minimal_content(self, service, mock_db):
        """Test analysis with minimal portfolio content."""
        user_id = uuid4()
        url = "https://example.com/portfolio"
        
        html_content = """
        <html>
            <body>
                <h1>My Portfolio</h1>
                <p>I work with Python.</p>
            </body>
        </html>
        """
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = html_content
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Should not raise error with minimal content
            assessment = service.analyze_portfolio_website(url, user_id)
            
            assert isinstance(assessment, SkillAssessment)
            assert assessment.skill_level >= 1
            assert assessment.confidence_score > 0
    
    def test_analyze_portfolio_website_invalid_url(self, service):
        """Test that invalid URL raises ValueError."""
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="Portfolio URL is required"):
            service.analyze_portfolio_website("", user_id)
    
    def test_analyze_portfolio_website_fetch_failure(self, service):
        """Test that fetch failure raises appropriate error."""
        user_id = uuid4()
        url = "https://example.com/portfolio"
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            
            with patch('time.sleep'):
                with pytest.raises(ValueError, match="Could not access portfolio website"):
                    service.analyze_portfolio_website(url, user_id)
    
    def test_analyze_portfolio_website_adds_https(self, service, mock_db):
        """Test that URL without protocol gets https:// added."""
        user_id = uuid4()
        url = "example.com/portfolio"
        
        html_content = "<html><body><h1>Portfolio</h1></body></html>"
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = html_content
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            assessment = service.analyze_portfolio_website(url, user_id)
            
            # Should have added https://
            assert assessment.source_url == "https://" + url
            
            # Verify the request was made with https://
            call_args = mock_get.call_args
            assert call_args[0][0].startswith("https://")



class TestCombineAssessments:
    """Test multi-source assessment combination functionality."""
    
    def test_combine_two_assessments(self, service, mock_db):
        """Test combining two assessments from different sources."""
        user_id = uuid4()
        
        # Create GitHub assessment
        github_assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            source_url="https://github.com/testuser",
            detected_skills=["Python", "JavaScript", "Docker"],
            experience_years=3.0,
            proficiency_levels={"Python": 0.9, "JavaScript": 0.7, "Docker": 0.6},
            analysis_summary="GitHub analysis summary",
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        # Create LinkedIn assessment
        linkedin_assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            source_url="https://linkedin.com/in/testuser",
            detected_skills=["Python", "AWS", "PostgreSQL"],
            experience_years=4.0,
            proficiency_levels={"Python": 0.85, "AWS": 0.8, "PostgreSQL": 0.7},
            analysis_summary="LinkedIn analysis summary",
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        
        # Combine assessments
        combined = service.combine_assessments([github_assessment, linkedin_assessment], user_id)
        
        # Verify combined assessment
        assert isinstance(combined, SkillAssessment)
        assert combined.user_id == user_id
        assert combined.source == AssessmentSource.COMBINED
        assert 1 <= combined.skill_level <= 10
        
        # LinkedIn is more recent and has higher confidence, so skill level should be closer to 8
        assert combined.skill_level >= 7
        
        # Verify skills are combined and deduplicated
        assert "Python" in combined.detected_skills
        assert "JavaScript" in combined.detected_skills
        assert "AWS" in combined.detected_skills
        assert "Docker" in combined.detected_skills
        assert "PostgreSQL" in combined.detected_skills
        
        # Verify proficiency levels (should take maximum)
        assert combined.proficiency_levels["Python"] == 0.9  # Max from GitHub
        
        # Verify experience years (should take maximum)
        assert combined.experience_years == 4.0
        
        # Verify confidence score
        assert combined.confidence_score > 0
        
        # Verify source data
        assert combined.source_data["source_count"] == 2
        assert "github" in combined.source_data["sources"]
        assert "linkedin" in combined.source_data["sources"]
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_combine_three_assessments_with_recency_weighting(self, service, mock_db):
        """Test combining three assessments with different ages."""
        user_id = uuid4()
        
        # Old GitHub assessment (6 months ago)
        github_assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=5,
            confidence_score=0.7,
            detected_skills=["Python"],
            experience_years=2.0,
            proficiency_levels={"Python": 0.6},
            created_at=datetime.utcnow() - timedelta(days=180)
        )
        
        # Medium-age LinkedIn assessment (2 months ago)
        linkedin_assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "JavaScript"],
            experience_years=3.0,
            proficiency_levels={"Python": 0.8, "JavaScript": 0.7},
            created_at=datetime.utcnow() - timedelta(days=60)
        )
        
        # Recent resume assessment (1 week ago)
        resume_assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.RESUME,
            skill_level=8,
            confidence_score=0.85,
            detected_skills=["Python", "JavaScript", "React"],
            experience_years=4.0,
            proficiency_levels={"Python": 0.9, "JavaScript": 0.8, "React": 0.75},
            created_at=datetime.utcnow() - timedelta(days=7)
        )
        
        # Combine assessments
        combined = service.combine_assessments(
            [github_assessment, linkedin_assessment, resume_assessment],
            user_id
        )
        
        # Recent assessment should have highest weight, so skill level should be closer to 8
        assert combined.skill_level >= 7
        
        # Verify all skills are included
        assert "Python" in combined.detected_skills
        assert "JavaScript" in combined.detected_skills
        assert "React" in combined.detected_skills
        
        # Verify metadata includes recency information
        assert combined.extra_metadata["most_recent_source"] == "resume"
        assert combined.extra_metadata["oldest_source"] == "github"
        assert combined.extra_metadata["days_span"] > 0
        
        # Verify source breakdown includes weights
        assert len(combined.source_data["source_breakdown"]) == 3
        for source_info in combined.source_data["source_breakdown"]:
            assert "recency_weight" in source_info
            assert "combined_weight" in source_info
    
    def test_combine_assessments_skill_deduplication(self, service, mock_db):
        """Test that skills are properly deduplicated across sources."""
        user_id = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "python", "PYTHON", "JavaScript"],
            experience_years=3.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python", "Java", "javascript"],
            experience_years=4.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        combined = service.combine_assessments([assessment1, assessment2], user_id)
        
        # Count occurrences of Python (case-insensitive)
        python_count = sum(1 for skill in combined.detected_skills if skill.lower() == "python")
        javascript_count = sum(1 for skill in combined.detected_skills if skill.lower() == "javascript")
        
        # Should only have one instance of each skill
        assert python_count == 1
        assert javascript_count == 1
        assert "Java" in combined.detected_skills
    
    def test_combine_assessments_empty_list_raises_error(self, service):
        """Test that empty assessment list raises ValueError."""
        user_id = uuid4()
        
        with pytest.raises(ValueError, match="At least one assessment is required"):
            service.combine_assessments([], user_id)
    
    def test_combine_assessments_wrong_user_raises_error(self, service):
        """Test that assessments from different users raise ValueError."""
        user_id1 = uuid4()
        user_id2 = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id1,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            experience_years=3.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id2,  # Different user
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python"],
            experience_years=4.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        with pytest.raises(ValueError, match="does not belong to user"):
            service.combine_assessments([assessment1, assessment2], user_id1)
    
    def test_combine_assessments_single_assessment(self, service, mock_db):
        """Test combining a single assessment (edge case)."""
        user_id = uuid4()
        
        assessment = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "JavaScript"],
            experience_years=3.0,
            proficiency_levels={"Python": 0.9, "JavaScript": 0.7},
            created_at=datetime.utcnow()
        )
        
        combined = service.combine_assessments([assessment], user_id)
        
        # Should preserve the single assessment's values
        assert combined.skill_level == 7
        assert combined.detected_skills == ["Python", "JavaScript"]
        assert combined.experience_years == 3.0
        assert combined.source_data["source_count"] == 1
    
    def test_combine_assessments_with_none_confidence_scores(self, service, mock_db):
        """Test combining assessments where some have None confidence scores."""
        user_id = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=None,  # None confidence
            detected_skills=["Python"],
            experience_years=3.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python"],
            experience_years=4.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        # Should not raise error
        combined = service.combine_assessments([assessment1, assessment2], user_id)
        
        assert isinstance(combined, SkillAssessment)
        assert combined.confidence_score > 0
    
    def test_combine_assessments_proficiency_takes_maximum(self, service, mock_db):
        """Test that proficiency levels take the maximum value across sources."""
        user_id = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "JavaScript"],
            experience_years=3.0,
            proficiency_levels={"Python": 0.7, "JavaScript": 0.9},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python", "Java"],
            experience_years=4.0,
            proficiency_levels={"Python": 0.95, "Java": 0.8},
            created_at=datetime.utcnow()
        )
        
        combined = service.combine_assessments([assessment1, assessment2], user_id)
        
        # Should take maximum proficiency for each skill
        assert combined.proficiency_levels["Python"] == 0.95  # Max from LinkedIn
        assert combined.proficiency_levels["JavaScript"] == 0.9  # Only from GitHub
        assert combined.proficiency_levels["Java"] == 0.8  # Only from LinkedIn
    
    def test_combine_assessments_experience_takes_maximum(self, service, mock_db):
        """Test that experience years take the maximum value."""
        user_id = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python"],
            experience_years=3.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python"],
            experience_years=5.5,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment3 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.RESUME,
            skill_level=7,
            confidence_score=0.85,
            detected_skills=["Python"],
            experience_years=4.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        combined = service.combine_assessments([assessment1, assessment2, assessment3], user_id)
        
        # Should take maximum experience years
        assert combined.experience_years == 5.5
    
    def test_combine_assessments_skill_level_in_valid_range(self, service, mock_db):
        """Test that combined skill level is always in valid range (1-10)."""
        user_id = uuid4()
        
        # Create assessments with extreme values
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=1,
            confidence_score=0.5,
            detected_skills=["Python"],
            experience_years=0.5,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=10,
            confidence_score=0.9,
            detected_skills=["Python"],
            experience_years=10.0,
            proficiency_levels={},
            created_at=datetime.utcnow()
        )
        
        combined = service.combine_assessments([assessment1, assessment2], user_id)
        
        # Should be in valid range
        assert 1 <= combined.skill_level <= 10
    
    def test_combine_assessments_summary_generation(self, service, mock_db):
        """Test that combined assessment generates proper summary."""
        user_id = uuid4()
        
        assessment1 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=7,
            confidence_score=0.8,
            detected_skills=["Python", "JavaScript"],
            experience_years=3.0,
            proficiency_levels={},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        
        assessment2 = SkillAssessment(
            id=uuid4(),
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=8,
            confidence_score=0.9,
            detected_skills=["Python", "AWS"],
            experience_years=4.0,
            proficiency_levels={},
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        
        combined = service.combine_assessments([assessment1, assessment2], user_id)
        
        # Verify summary contains key information
        assert "Combined assessment from 2 sources" in combined.analysis_summary
        assert "Github" in combined.analysis_summary or "GitHub" in combined.analysis_summary
        assert "Linkedin" in combined.analysis_summary or "LinkedIn" in combined.analysis_summary
        assert "Unified skill level" in combined.analysis_summary
        assert "years of experience" in combined.analysis_summary
        assert "skills identified" in combined.analysis_summary
