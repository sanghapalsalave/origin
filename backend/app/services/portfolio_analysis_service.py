"""
Portfolio Analysis Service

Analyzes user portfolios from multiple sources to assess skill levels.

Implements Requirements:
- 13.1: GitHub URL data retrieval
- 13.2: GitHub repository analysis (languages, commit frequency, project complexity)
- 13.3: LinkedIn data retrieval (work experience, skills, endorsements, certifications)
- 13.4: LinkedIn experience recency weighting
- 13.12: API rate limit handling with exponential backoff
- 2.1: Vector embedding generation for matching
"""
import time
import logging
import requests
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from github import Github, GithubException, RateLimitExceededException, Auth
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings
from app.core.retry import retry_with_exponential_backoff, RetryConfig
from app.models.skill_assessment import SkillAssessment, AssessmentSource, VectorEmbedding
from sqlalchemy.orm import Session
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class PortfolioAnalysisService:
    """Service for analyzing user portfolios from multiple sources."""
    
    def __init__(self, db: Session):
        """
        Initialize portfolio analysis service.
        
        Args:
            db: Database session for storing assessments
        """
        self.db = db
        self.github_client = None
        if settings.GITHUB_TOKEN:
            auth = Auth.Token(settings.GITHUB_TOKEN)
            self.github_client = Github(auth=auth)
    
    def analyze_github(self, github_url: str, user_id: UUID) -> SkillAssessment:
        """
        Analyze GitHub profile and repositories.
        
        Extracts repository languages, commit frequency, and project complexity
        to generate a skill level assessment (1-10).
        
        Implements Requirements:
        - 13.1: Retrieve public repository data via GitHub API
        - 13.2: Evaluate repository languages, commit frequency, and project complexity
        - 13.12: Handle API rate limits with exponential backoff
        
        Args:
            github_url: GitHub profile URL (e.g., https://github.com/username)
            user_id: User ID for associating the assessment
            
        Returns:
            SkillAssessment object with skill level (1-10) and detected technologies
            
        Raises:
            ValueError: If GitHub URL is invalid or user not found
            Exception: If GitHub API fails after retries
        """
        if not self.github_client:
            raise ValueError("GitHub token not configured")
        
        # Extract username from URL
        username = self._extract_github_username(github_url)
        if not username:
            raise ValueError(f"Invalid GitHub URL: {github_url}")
        
        # Fetch user data with retry logic
        try:
            user_data = self._fetch_github_user_with_retry(username)
            repos_data = self._fetch_github_repos_with_retry(username)
        except Exception as e:
            logger.error(f"Failed to fetch GitHub data for {username}: {str(e)}")
            raise
        
        # Analyze repositories
        analysis = self._analyze_github_repositories(repos_data)
        
        # Calculate skill level (1-10)
        skill_level = self._calculate_github_skill_level(analysis, user_data)
        
        # Create skill assessment
        assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.GITHUB,
            skill_level=skill_level,
            confidence_score=analysis["confidence_score"],
            source_url=github_url,
            source_data={
                "username": username,
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "following": user_data.get("following", 0),
                "created_at": user_data.get("created_at"),
                "repositories": analysis["repositories_summary"]
            },
            detected_skills=analysis["languages"],
            experience_years=analysis["estimated_experience_years"],
            proficiency_levels=analysis["language_proficiency"],
            analysis_summary=analysis["summary"],
            extra_metadata={
                "total_commits": analysis["total_commits"],
                "avg_commits_per_repo": analysis["avg_commits_per_repo"],
                "commit_frequency_score": analysis["commit_frequency_score"],
                "project_complexity_score": analysis["project_complexity_score"],
                "total_stars": analysis["total_stars"],
                "total_forks": analysis["total_forks"],
                "active_repos": analysis["active_repos"]
            }
        )
        
        # Save to database
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(f"GitHub analysis completed for user {user_id}: skill_level={skill_level}")
        return assessment
    
    def _extract_github_username(self, github_url: str) -> Optional[str]:
        """
        Extract username from GitHub URL.
        
        Args:
            github_url: GitHub profile URL
            
        Returns:
            Username or None if invalid
        """
        # Handle various GitHub URL formats
        # https://github.com/username
        # github.com/username
        # username
        github_url = github_url.strip().rstrip('/')
        
        if github_url.startswith('http://') or github_url.startswith('https://'):
            parts = github_url.split('/')
            if len(parts) >= 4 and 'github.com' in parts[2]:
                return parts[3]
        elif github_url.startswith('github.com/'):
            parts = github_url.split('/')
            if len(parts) >= 2:
                return parts[1]
        elif '/' not in github_url and '@' not in github_url:
            # Assume it's just a username
            return github_url
        
        return None
    
    @retry_with_exponential_backoff(
        max_retries=RetryConfig.GITHUB_MAX_RETRIES,
        base_delay=RetryConfig.GITHUB_BASE_DELAY,
        max_delay=RetryConfig.GITHUB_MAX_DELAY,
        exceptions=(RateLimitExceededException, GithubException)
    )
    def _fetch_github_user_with_retry(self, username: str, max_retries: int = 5) -> Dict[str, Any]:
        """
        Fetch GitHub user data with exponential backoff retry.
        
        Implements Requirement 13.12: API retry with exponential backoff
        
        Args:
            username: GitHub username
            max_retries: Maximum number of retry attempts (deprecated, uses decorator config)
            
        Returns:
            User data dictionary
            
        Raises:
            ValueError: If GitHub user not found
            Exception: If all retries fail
        """
        try:
            user = self.github_client.get_user(username)
            return {
                "username": user.login,
                "name": user.name,
                "public_repos": user.public_repos,
                "followers": user.followers,
                "following": user.following,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "bio": user.bio,
                "company": user.company,
                "location": user.location
            }
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"GitHub user not found: {username}")
            # Let other exceptions be handled by the retry decorator
            raise
    
    @retry_with_exponential_backoff(
        max_retries=RetryConfig.GITHUB_MAX_RETRIES,
        base_delay=RetryConfig.GITHUB_BASE_DELAY,
        max_delay=RetryConfig.GITHUB_MAX_DELAY,
        exceptions=(RateLimitExceededException, GithubException)
    )
    def _fetch_github_repos_with_retry(self, username: str, max_retries: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch GitHub repositories with exponential backoff retry.
        
        Implements Requirement 13.12: API retry with exponential backoff
        
        Args:
            username: GitHub username
            max_retries: Maximum number of retry attempts (deprecated, uses decorator config)
            
        Returns:
            List of repository data dictionaries
            
        Raises:
            Exception: If all retries fail
        """
        user = self.github_client.get_user(username)
        repos = []
        
        # Fetch up to 100 most recent repositories
        for repo in user.get_repos(sort='updated', direction='desc')[:100]:
            # Skip forks unless they have significant activity
            if repo.fork and repo.stargazers_count < 5:
                continue
            
            repo_data = {
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "languages": self._fetch_repo_languages_with_retry(repo, max_retries=3),
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "size": repo.size,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                "is_fork": repo.fork,
                "open_issues": repo.open_issues_count,
                "has_wiki": repo.has_wiki,
                "has_pages": repo.has_pages
            }
            
            # Fetch commit count (with retry)
            try:
                commits = repo.get_commits()
                repo_data["commit_count"] = commits.totalCount
            except Exception as e:
                logger.warning(f"Could not fetch commits for {repo.name}: {str(e)}")
                repo_data["commit_count"] = 0
            
            repos.append(repo_data)
        
        return repos
    
    @retry_with_exponential_backoff(
        max_retries=3,
        base_delay=1.0,
        max_delay=16.0,
        exceptions=(RateLimitExceededException, GithubException)
    )
    def _fetch_repo_languages_with_retry(self, repo, max_retries: int = 3) -> Dict[str, int]:
        """
        Fetch repository languages with retry logic.
        
        Args:
            repo: GitHub repository object
            max_retries: Maximum retry attempts (deprecated, uses decorator config)
            
        Returns:
            Dictionary of language: bytes_of_code
        """
        try:
            return repo.get_languages()
        except Exception as e:
            logger.warning(f"Could not fetch languages for {repo.name}: {str(e)}")
            return {}
    
    def _analyze_github_repositories(self, repos_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze GitHub repositories to extract skill indicators.
        
        Implements Requirement 13.2: Evaluate repository languages, commit frequency,
        and project complexity.
        
        Args:
            repos_data: List of repository data dictionaries
            
        Returns:
            Analysis dictionary with languages, commit frequency, complexity scores
        """
        if not repos_data:
            return {
                "languages": [],
                "language_proficiency": {},
                "total_commits": 0,
                "avg_commits_per_repo": 0,
                "commit_frequency_score": 0,
                "project_complexity_score": 0,
                "total_stars": 0,
                "total_forks": 0,
                "active_repos": 0,
                "estimated_experience_years": 0,
                "confidence_score": 0.1,
                "summary": "No repositories found",
                "repositories_summary": []
            }
        
        # Aggregate language usage
        language_bytes = {}
        for repo in repos_data:
            if repo.get("languages"):
                for lang, bytes_count in repo["languages"].items():
                    if lang:  # Skip None/empty languages
                        language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count
        
        # Sort languages by usage
        sorted_languages = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)
        top_languages = [lang for lang, _ in sorted_languages[:10]]
        
        # Calculate language proficiency (normalized by total bytes)
        total_bytes = sum(language_bytes.values()) if language_bytes else 1
        language_proficiency = {
            lang: round(bytes_count / total_bytes, 3)
            for lang, bytes_count in sorted_languages[:10]
        }
        
        # Calculate commit metrics
        total_commits = sum(repo.get("commit_count", 0) for repo in repos_data)
        avg_commits_per_repo = total_commits / len(repos_data) if repos_data else 0
        
        # Calculate commit frequency score (based on recent activity)
        now = datetime.utcnow()
        active_repos = 0
        recent_commits = 0
        
        for repo in repos_data:
            if repo.get("pushed_at"):
                try:
                    pushed_at = datetime.fromisoformat(repo["pushed_at"].replace('Z', '+00:00'))
                    days_since_push = (now - pushed_at.replace(tzinfo=None)).days
                    
                    if days_since_push < 90:  # Active in last 3 months
                        active_repos += 1
                        recent_commits += repo.get("commit_count", 0)
                except Exception as e:
                    logger.warning(f"Error parsing date: {str(e)}")
        
        # Commit frequency score (0-10)
        commit_frequency_score = min(10, (recent_commits / 50) * 10) if recent_commits > 0 else 0
        
        # Calculate project complexity score
        total_stars = sum(repo.get("stars", 0) for repo in repos_data)
        total_forks = sum(repo.get("forks", 0) for repo in repos_data)
        avg_repo_size = sum(repo.get("size", 0) for repo in repos_data) / len(repos_data) if repos_data else 0
        
        # Complexity factors
        complexity_factors = {
            "stars": min(10, (total_stars / 100) * 10),
            "forks": min(10, (total_forks / 20) * 10),
            "repo_size": min(10, (avg_repo_size / 1000) * 10),
            "repo_count": min(10, (len(repos_data) / 20) * 10),
            "language_diversity": min(10, len(top_languages))
        }
        
        project_complexity_score = sum(complexity_factors.values()) / len(complexity_factors)
        
        # Estimate experience years (based on account age and activity)
        estimated_experience_years = 0
        if repos_data and repos_data[0].get("created_at"):
            try:
                oldest_repo = min(
                    (datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))
                     for r in repos_data if r.get("created_at")),
                    default=None
                )
                if oldest_repo:
                    years = (now - oldest_repo.replace(tzinfo=None)).days / 365.25
                    estimated_experience_years = round(min(years, 20), 1)  # Cap at 20 years
            except Exception as e:
                logger.warning(f"Error calculating experience years: {str(e)}")
        
        # Calculate confidence score (0-1)
        confidence_score = min(1.0, (
            (len(repos_data) / 50) * 0.3 +  # More repos = higher confidence
            (total_commits / 500) * 0.3 +    # More commits = higher confidence
            (active_repos / 10) * 0.2 +      # Recent activity = higher confidence
            (len(top_languages) / 10) * 0.2  # Language diversity = higher confidence
        ))
        
        # Generate summary
        summary = self._generate_github_summary(
            repos_data, top_languages, total_commits, active_repos,
            estimated_experience_years, project_complexity_score
        )
        
        # Create repositories summary (top 10 most significant)
        repos_summary = sorted(
            repos_data,
            key=lambda r: (r.get("stars", 0) * 2 + r.get("forks", 0) + r.get("commit_count", 0)),
            reverse=True
        )[:10]
        
        return {
            "languages": top_languages,
            "language_proficiency": language_proficiency,
            "total_commits": total_commits,
            "avg_commits_per_repo": round(avg_commits_per_repo, 1),
            "commit_frequency_score": round(commit_frequency_score, 2),
            "project_complexity_score": round(project_complexity_score, 2),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "active_repos": active_repos,
            "estimated_experience_years": estimated_experience_years,
            "confidence_score": round(confidence_score, 3),
            "summary": summary,
            "repositories_summary": [
                {
                    "name": r["name"],
                    "language": r["language"],
                    "stars": r["stars"],
                    "forks": r["forks"],
                    "commits": r.get("commit_count", 0)
                }
                for r in repos_summary
            ]
        }
    
    def _calculate_github_skill_level(
        self,
        analysis: Dict[str, Any],
        user_data: Dict[str, Any]
    ) -> int:
        """
        Calculate skill level (1-10) based on GitHub analysis.
        
        Args:
            analysis: Repository analysis results
            user_data: GitHub user data
            
        Returns:
            Skill level between 1 and 10
        """
        # Weighted scoring factors
        scores = {
            "commit_frequency": analysis["commit_frequency_score"] * 0.25,
            "project_complexity": analysis["project_complexity_score"] * 0.25,
            "experience": min(10, analysis["estimated_experience_years"] * 2) * 0.20,
            "community": min(10, (user_data.get("followers", 0) / 50) * 10) * 0.15,
            "activity": min(10, (analysis["active_repos"] / 5) * 10) * 0.15
        }
        
        # Calculate weighted average
        total_score = sum(scores.values())
        
        # Convert to 1-10 scale (ensure minimum of 1)
        skill_level = max(1, min(10, round(total_score)))
        
        return skill_level
    
    def _generate_github_summary(
        self,
        repos_data: List[Dict[str, Any]],
        top_languages: List[str],
        total_commits: int,
        active_repos: int,
        experience_years: float,
        complexity_score: float
    ) -> str:
        """
        Generate human-readable summary of GitHub analysis.
        
        Args:
            repos_data: Repository data
            top_languages: Top programming languages
            total_commits: Total commit count
            active_repos: Number of recently active repositories
            experience_years: Estimated years of experience
            complexity_score: Project complexity score
            
        Returns:
            Summary string
        """
        lang_str = ", ".join(top_languages[:3]) if top_languages else "various languages"
        
        summary = (
            f"GitHub profile shows {len(repos_data)} repositories with "
            f"{total_commits} total commits. Primary languages: {lang_str}. "
            f"{active_repos} repositories active in the last 3 months. "
            f"Estimated {experience_years} years of experience. "
            f"Project complexity score: {complexity_score:.1f}/10."
        )
        
        return summary
    
    def analyze_linkedin(self, linkedin_profile: Dict[str, Any], user_id: UUID) -> SkillAssessment:
        """
        Analyze LinkedIn work experience and skills.
        
        Extracts work experience, skills, endorsements, and certifications
        to generate a skill level assessment (1-10). Implements recency weighting
        where more recent experience is weighted more heavily.
        
        Implements Requirements:
        - 13.3: Retrieve work experience, skills, endorsements, and certifications via LinkedIn API
        - 13.4: Weight recent experience more heavily than older positions
        
        Args:
            linkedin_profile: LinkedIn profile data dictionary containing:
                - positions: List of work experience positions
                - skills: List of skills with endorsement counts
                - certifications: List of certifications
                - education: Educational background
                - profile_url: LinkedIn profile URL (optional)
            user_id: User ID for associating the assessment
            
        Returns:
            SkillAssessment object with skill level (1-10) and experience summary
            
        Raises:
            ValueError: If LinkedIn profile data is invalid or missing required fields
        """
        if not linkedin_profile:
            raise ValueError("LinkedIn profile data is required")
        
        # Validate required fields
        if "positions" not in linkedin_profile and "skills" not in linkedin_profile:
            raise ValueError("LinkedIn profile must contain at least positions or skills data")
        
        # Extract and analyze work experience
        positions = linkedin_profile.get("positions", [])
        experience_analysis = self._analyze_linkedin_experience(positions)
        
        # Extract and analyze skills
        skills = linkedin_profile.get("skills", [])
        skills_analysis = self._analyze_linkedin_skills(skills)
        
        # Extract certifications
        certifications = linkedin_profile.get("certifications", [])
        certifications_analysis = self._analyze_linkedin_certifications(certifications)
        
        # Extract education
        education = linkedin_profile.get("education", [])
        education_analysis = self._analyze_linkedin_education(education)
        
        # Calculate skill level (1-10) with recency weighting
        skill_level = self._calculate_linkedin_skill_level(
            experience_analysis,
            skills_analysis,
            certifications_analysis,
            education_analysis
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_linkedin_confidence(
            experience_analysis,
            skills_analysis,
            certifications_analysis
        )
        
        # Generate summary
        summary = self._generate_linkedin_summary(
            experience_analysis,
            skills_analysis,
            certifications_analysis,
            education_analysis
        )
        
        # Combine detected skills from all sources
        detected_skills = list(set(
            skills_analysis["top_skills"] +
            experience_analysis["technologies"] +
            certifications_analysis["skill_areas"]
        ))[:20]  # Limit to top 20
        
        # Create skill assessment
        assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.LINKEDIN,
            skill_level=skill_level,
            confidence_score=confidence_score,
            source_url=linkedin_profile.get("profile_url"),
            source_data={
                "positions_count": len(positions),
                "skills_count": len(skills),
                "certifications_count": len(certifications),
                "education_count": len(education),
                "total_endorsements": skills_analysis["total_endorsements"],
                "experience_summary": experience_analysis["summary"],
                "top_skills": skills_analysis["top_skills"][:10],
                "recent_positions": experience_analysis["recent_positions"][:5]
            },
            detected_skills=detected_skills,
            experience_years=experience_analysis["total_years"],
            proficiency_levels=skills_analysis["skill_proficiency"],
            analysis_summary=summary,
            extra_metadata={
                "recency_weighted_score": experience_analysis["recency_weighted_score"],
                "skills_endorsement_score": skills_analysis["endorsement_score"],
                "certifications_score": certifications_analysis["score"],
                "education_score": education_analysis["score"],
                "current_positions": experience_analysis["current_positions_count"],
                "recent_experience_years": experience_analysis["recent_experience_years"],
                "skill_diversity": len(detected_skills)
            }
        )
        
        # Save to database
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(f"LinkedIn analysis completed for user {user_id}: skill_level={skill_level}")
        return assessment
    
    def _analyze_linkedin_experience(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze LinkedIn work experience with recency weighting.
        
        Implements Requirement 13.4: Weight recent experience more heavily than older positions.
        
        Args:
            positions: List of position dictionaries with title, company, start_date, end_date, description
            
        Returns:
            Analysis dictionary with experience metrics and recency-weighted scores
        """
        if not positions:
            return {
                "total_years": 0,
                "recent_experience_years": 0,
                "current_positions_count": 0,
                "recency_weighted_score": 0,
                "technologies": [],
                "recent_positions": [],
                "summary": "No work experience found"
            }
        
        now = datetime.utcnow()
        total_months = 0
        recent_months = 0  # Last 3 years
        current_positions_count = 0
        position_scores = []
        technologies = []
        recent_positions = []
        
        for position in positions:
            # Parse dates
            start_date = self._parse_linkedin_date(position.get("start_date"))
            end_date = self._parse_linkedin_date(position.get("end_date")) or now
            
            if not start_date:
                continue
            
            # Calculate duration in months
            duration_months = self._calculate_months_between(start_date, end_date)
            total_months += duration_months
            
            # Check if current position
            is_current = position.get("is_current", False) or not position.get("end_date")
            if is_current:
                current_positions_count += 1
            
            # Calculate recency weight (exponential decay)
            # Positions in last year: weight = 1.0
            # Positions 1-3 years ago: weight = 0.7
            # Positions 3-5 years ago: weight = 0.4
            # Positions 5+ years ago: weight = 0.2
            years_ago = (now - start_date).days / 365.25
            if years_ago < 1:
                recency_weight = 1.0
                recent_months += duration_months
            elif years_ago < 3:
                recency_weight = 0.7
                recent_months += duration_months
            elif years_ago < 5:
                recency_weight = 0.4
            else:
                recency_weight = 0.2
            
            # Calculate position score (duration * recency weight)
            position_score = (duration_months / 12) * recency_weight
            position_scores.append(position_score)
            
            # Extract technologies from description
            if position.get("description"):
                extracted_tech = self._extract_technologies_from_text(position["description"])
                technologies.extend(extracted_tech)
            
            # Track recent positions (last 3 years)
            if years_ago < 3:
                recent_positions.append({
                    "title": position.get("title", "Unknown"),
                    "company": position.get("company", "Unknown"),
                    "duration_months": duration_months,
                    "is_current": is_current
                })
        
        # Calculate total experience years
        total_years = round(total_months / 12, 1)
        recent_experience_years = round(recent_months / 12, 1)
        
        # Calculate recency-weighted score (0-10)
        recency_weighted_score = min(10, sum(position_scores))
        
        # Get unique technologies
        unique_technologies = list(set(technologies))[:15]
        
        return {
            "total_years": total_years,
            "recent_experience_years": recent_experience_years,
            "current_positions_count": current_positions_count,
            "recency_weighted_score": round(recency_weighted_score, 2),
            "technologies": unique_technologies,
            "recent_positions": recent_positions,
            "summary": f"{total_years} years total experience, {recent_experience_years} years recent"
        }
    
    def _analyze_linkedin_skills(self, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze LinkedIn skills and endorsements.
        
        Args:
            skills: List of skill dictionaries with name and endorsement_count
            
        Returns:
            Analysis dictionary with skill metrics and endorsement scores
        """
        if not skills:
            return {
                "top_skills": [],
                "total_endorsements": 0,
                "endorsement_score": 0,
                "skill_proficiency": {}
            }
        
        # Sort skills by endorsement count
        sorted_skills = sorted(
            skills,
            key=lambda s: s.get("endorsement_count", 0),
            reverse=True
        )
        
        # Calculate total endorsements
        total_endorsements = sum(s.get("endorsement_count", 0) for s in skills)
        
        # Calculate endorsement score (0-10)
        # 50+ endorsements = 10, scale linearly
        endorsement_score = min(10, (total_endorsements / 50) * 10)
        
        # Get top skills
        top_skills = [s.get("name") for s in sorted_skills[:15] if s.get("name")]
        
        # Calculate skill proficiency (normalized by endorsements)
        max_endorsements = sorted_skills[0].get("endorsement_count", 1) if sorted_skills else 1
        skill_proficiency = {}
        
        for skill in sorted_skills[:15]:
            skill_name = skill.get("name")
            endorsements = skill.get("endorsement_count", 0)
            if skill_name:
                # Normalize to 0-1 scale
                proficiency = endorsements / max_endorsements if max_endorsements > 0 else 0
                skill_proficiency[skill_name] = round(proficiency, 3)
        
        return {
            "top_skills": top_skills,
            "total_endorsements": total_endorsements,
            "endorsement_score": round(endorsement_score, 2),
            "skill_proficiency": skill_proficiency
        }
    
    def _analyze_linkedin_certifications(self, certifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze LinkedIn certifications.
        
        Args:
            certifications: List of certification dictionaries with name, authority, date
            
        Returns:
            Analysis dictionary with certification metrics
        """
        if not certifications:
            return {
                "score": 0,
                "skill_areas": [],
                "recent_certifications": []
            }
        
        now = datetime.utcnow()
        recent_certs = []
        skill_areas = []
        
        for cert in certifications:
            # Extract skill areas from certification name
            cert_name = cert.get("name", "")
            extracted_skills = self._extract_technologies_from_text(cert_name)
            skill_areas.extend(extracted_skills)
            
            # Check if recent (last 2 years)
            cert_date = self._parse_linkedin_date(cert.get("date"))
            if cert_date and (now - cert_date).days < 730:  # 2 years
                recent_certs.append(cert_name)
        
        # Calculate certification score (0-10)
        # 1 cert = 2 points, 5+ certs = 10 points
        cert_score = min(10, len(certifications) * 2)
        
        # Bonus for recent certifications
        if recent_certs:
            cert_score = min(10, cert_score + len(recent_certs) * 0.5)
        
        return {
            "score": round(cert_score, 2),
            "skill_areas": list(set(skill_areas)),
            "recent_certifications": recent_certs
        }
    
    def _analyze_linkedin_education(self, education: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze LinkedIn education background.
        
        Args:
            education: List of education dictionaries with school, degree, field_of_study
            
        Returns:
            Analysis dictionary with education metrics
        """
        if not education:
            return {
                "score": 0,
                "highest_degree": None
            }
        
        # Degree ranking for scoring
        degree_scores = {
            "phd": 10,
            "doctorate": 10,
            "master": 8,
            "mba": 8,
            "bachelor": 6,
            "associate": 4,
            "certificate": 2
        }
        
        highest_score = 0
        highest_degree = None
        
        for edu in education:
            degree = edu.get("degree", "").lower()
            for degree_type, score in degree_scores.items():
                if degree_type in degree:
                    if score > highest_score:
                        highest_score = score
                        highest_degree = edu.get("degree")
                    break
        
        return {
            "score": highest_score,
            "highest_degree": highest_degree
        }
    
    def _calculate_linkedin_skill_level(
        self,
        experience_analysis: Dict[str, Any],
        skills_analysis: Dict[str, Any],
        certifications_analysis: Dict[str, Any],
        education_analysis: Dict[str, Any]
    ) -> int:
        """
        Calculate skill level (1-10) based on LinkedIn analysis with recency weighting.
        
        Implements Requirement 13.4: Recent experience weighted more heavily.
        
        Args:
            experience_analysis: Work experience analysis
            skills_analysis: Skills and endorsements analysis
            certifications_analysis: Certifications analysis
            education_analysis: Education analysis
            
        Returns:
            Skill level between 1 and 10
        """
        # Weighted scoring factors (recency-weighted experience has highest weight)
        scores = {
            "recency_weighted_experience": experience_analysis["recency_weighted_score"] * 0.40,
            "skills_endorsements": skills_analysis["endorsement_score"] * 0.25,
            "certifications": certifications_analysis["score"] * 0.20,
            "education": education_analysis["score"] * 0.15
        }
        
        # Calculate weighted average
        total_score = sum(scores.values())
        
        # Convert to 1-10 scale (ensure minimum of 1)
        skill_level = max(1, min(10, round(total_score)))
        
        return skill_level
    
    def _calculate_linkedin_confidence(
        self,
        experience_analysis: Dict[str, Any],
        skills_analysis: Dict[str, Any],
        certifications_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate confidence score (0-1) for LinkedIn assessment.
        
        Args:
            experience_analysis: Work experience analysis
            skills_analysis: Skills analysis
            certifications_analysis: Certifications analysis
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence_factors = []
        
        # Experience completeness
        if experience_analysis["total_years"] > 0:
            confidence_factors.append(min(1.0, experience_analysis["total_years"] / 10))
        
        # Skills with endorsements
        if skills_analysis["total_endorsements"] > 0:
            confidence_factors.append(min(1.0, skills_analysis["total_endorsements"] / 50))
        
        # Certifications
        if certifications_analysis["score"] > 0:
            confidence_factors.append(min(1.0, certifications_analysis["score"] / 10))
        
        # Current employment
        if experience_analysis["current_positions_count"] > 0:
            confidence_factors.append(0.8)
        
        # Calculate average confidence
        confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.1
        
        return round(confidence, 3)
    
    def _generate_linkedin_summary(
        self,
        experience_analysis: Dict[str, Any],
        skills_analysis: Dict[str, Any],
        certifications_analysis: Dict[str, Any],
        education_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable summary of LinkedIn analysis.
        
        Args:
            experience_analysis: Work experience analysis
            skills_analysis: Skills analysis
            certifications_analysis: Certifications analysis
            education_analysis: Education analysis
            
        Returns:
            Summary string
        """
        parts = []
        
        # Experience
        if experience_analysis["total_years"] > 0:
            parts.append(
                f"{experience_analysis['total_years']} years of experience "
                f"({experience_analysis['recent_experience_years']} years recent)"
            )
        
        # Skills
        if skills_analysis["top_skills"]:
            top_3_skills = ", ".join(skills_analysis["top_skills"][:3])
            parts.append(
                f"Top skills: {top_3_skills} "
                f"({skills_analysis['total_endorsements']} total endorsements)"
            )
        
        # Certifications
        cert_count = len(certifications_analysis.get("recent_certifications", []))
        if cert_count > 0:
            parts.append(f"{cert_count} recent certifications")
        
        # Education
        if education_analysis["highest_degree"]:
            parts.append(f"Education: {education_analysis['highest_degree']}")
        
        # Current employment
        if experience_analysis["current_positions_count"] > 0:
            parts.append("Currently employed")
        
        summary = ". ".join(parts) + "." if parts else "Limited LinkedIn profile data available."
        
        return summary
    
    def _parse_linkedin_date(self, date_value: Any) -> Optional[datetime]:
        """
        Parse LinkedIn date value (can be string, dict, or datetime).
        
        Args:
            date_value: Date value from LinkedIn API
            
        Returns:
            datetime object or None if parsing fails
        """
        if not date_value:
            return None
        
        try:
            # If already datetime
            if isinstance(date_value, datetime):
                return date_value
            
            # If dict with year/month (LinkedIn API format)
            if isinstance(date_value, dict):
                year = date_value.get("year")
                month = date_value.get("month", 1)
                if year:
                    return datetime(year, month, 1)
            
            # If string, try to parse
            if isinstance(date_value, str):
                # Try ISO format
                try:
                    return datetime.fromisoformat(date_value.replace('Z', '+00:00')).replace(tzinfo=None)
                except:
                    pass
                
                # Try common formats
                for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except:
                        continue
        
        except Exception as e:
            logger.warning(f"Error parsing LinkedIn date {date_value}: {str(e)}")
        
        return None
    
    def _calculate_months_between(self, start_date: datetime, end_date: datetime) -> int:
        """
        Calculate number of months between two dates.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Number of months
        """
        months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
        return max(0, months)
    
    def _extract_technologies_from_text(self, text: str) -> List[str]:
        """
        Extract technology keywords from text (job descriptions, certifications, etc.).
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected technology keywords
        """
        if not text:
            return []
        
        # Common technology keywords to look for
        tech_keywords = [
            "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
            "php", "swift", "kotlin", "scala", "r", "matlab",
            "react", "angular", "vue", "node", "django", "flask", "spring", "express",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "machine learning", "deep learning", "ai", "data science", "nlp",
            "devops", "ci/cd", "jenkins", "github actions",
            "rest", "graphql", "api", "microservices",
            "agile", "scrum", "jira"
        ]
        
        text_lower = text.lower()
        found_technologies = []
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                # Capitalize properly
                found_technologies.append(keyword.title())
        
        return found_technologies

    
    def parse_resume(self, file_content: bytes, file_type: str, user_id: UUID) -> SkillAssessment:
        """
        Parse resume (PDF/DOCX/TXT) and extract skills.
        
        Extracts skills, experience, and education from resume files using
        PyPDF2, python-docx for parsing and spaCy for NLP skill extraction.
        
        Implements Requirements:
        - 13.5: Parse PDF, DOCX, TXT formats
        - 13.6: Use NLP for skill extraction and proficiency identification
        
        Args:
            file_content: Raw file content as bytes
            file_type: File type ('pdf', 'docx', 'txt')
            user_id: User ID for associating the assessment
            
        Returns:
            SkillAssessment object with skill level (1-10) and experience data
            
        Raises:
            ValueError: If file type is unsupported or parsing fails
        """
        from app.services.resume_parser import ResumeParser
        
        # Parse resume using ResumeParser
        parser = ResumeParser()
        try:
            parsed_data = parser.parse_resume(file_content, file_type)
        except Exception as e:
            logger.error(f"Failed to parse resume: {str(e)}")
            raise
        
        # Extract parsed information
        skills = parsed_data["skills"]
        experience_entries = parsed_data["experience"]
        education_entries = parsed_data["education"]
        proficiency_levels = parsed_data["proficiency_levels"]
        experience_years = parsed_data["experience_years"]
        contact_info = parsed_data["contact_info"]
        
        # Calculate skill level (1-10) based on resume analysis
        skill_level = self._calculate_resume_skill_level(
            skills,
            experience_years,
            education_entries,
            proficiency_levels
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_resume_confidence(
            skills,
            experience_entries,
            education_entries,
            len(parsed_data["text"])
        )
        
        # Generate summary
        summary = self._generate_resume_summary(
            skills,
            experience_years,
            experience_entries,
            education_entries
        )
        
        # Create skill assessment
        assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.RESUME,
            skill_level=skill_level,
            confidence_score=confidence_score,
            source_url=None,  # Resume files don't have URLs
            source_data={
                "file_type": file_type,
                "text_length": len(parsed_data["text"]),
                "skills_count": len(skills),
                "experience_count": len(experience_entries),
                "education_count": len(education_entries),
                "contact_info": contact_info,
                "experience_entries": experience_entries[:5],  # Store top 5
                "education_entries": education_entries
            },
            detected_skills=skills,
            experience_years=experience_years,
            proficiency_levels=proficiency_levels,
            analysis_summary=summary,
            extra_metadata={
                "has_contact_info": any(contact_info.values()),
                "has_github": bool(contact_info.get("github")),
                "has_linkedin": bool(contact_info.get("linkedin")),
                "skill_diversity": len(skills),
                "avg_proficiency": round(sum(proficiency_levels.values()) / len(proficiency_levels), 2) if proficiency_levels else 0
            }
        )
        
        # Save to database
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(f"Resume analysis completed for user {user_id}: skill_level={skill_level}, skills={len(skills)}")
        return assessment
    
    def _calculate_resume_skill_level(
        self,
        skills: List[str],
        experience_years: float,
        education: List[Dict[str, Any]],
        proficiency_levels: Dict[str, float]
    ) -> int:
        """
        Calculate skill level (1-10) based on resume analysis.
        
        Args:
            skills: List of detected skills
            experience_years: Years of experience
            education: Education entries
            proficiency_levels: Skill proficiency levels
            
        Returns:
            Skill level between 1 and 10
        """
        # Weighted scoring factors
        scores = {}
        
        # Experience score (0-10)
        # 0-1 years = 2, 1-3 years = 4, 3-5 years = 6, 5-10 years = 8, 10+ years = 10
        if experience_years < 1:
            scores["experience"] = 2
        elif experience_years < 3:
            scores["experience"] = 4
        elif experience_years < 5:
            scores["experience"] = 6
        elif experience_years < 10:
            scores["experience"] = 8
        else:
            scores["experience"] = 10
        
        # Skills diversity score (0-10)
        # 1-5 skills = 2, 5-10 = 5, 10-15 = 7, 15-20 = 9, 20+ = 10
        skill_count = len(skills)
        if skill_count < 5:
            scores["skills_diversity"] = min(10, skill_count * 2)
        elif skill_count < 10:
            scores["skills_diversity"] = 5
        elif skill_count < 15:
            scores["skills_diversity"] = 7
        elif skill_count < 20:
            scores["skills_diversity"] = 9
        else:
            scores["skills_diversity"] = 10
        
        # Proficiency score (0-10)
        if proficiency_levels:
            avg_proficiency = sum(proficiency_levels.values()) / len(proficiency_levels)
            scores["proficiency"] = avg_proficiency * 10
        else:
            scores["proficiency"] = 5  # Default medium
        
        # Education score (0-10)
        education_score = 0
        if education:
            # Check for advanced degrees
            for edu in education:
                degree = edu.get("degree", "").lower()
                if "phd" in degree or "doctorate" in degree:
                    education_score = 10
                    break
                elif "master" in degree or "mba" in degree:
                    education_score = max(education_score, 8)
                elif "bachelor" in degree:
                    education_score = max(education_score, 6)
                elif "associate" in degree:
                    education_score = max(education_score, 4)
        scores["education"] = education_score
        
        # Calculate weighted average
        # Experience and proficiency are most important for skill level
        weighted_score = (
            scores["experience"] * 0.40 +
            scores["proficiency"] * 0.30 +
            scores["skills_diversity"] * 0.20 +
            scores["education"] * 0.10
        )
        
        # Convert to 1-10 scale (ensure minimum of 1)
        skill_level = max(1, min(10, round(weighted_score)))
        
        return skill_level
    
    def _calculate_resume_confidence(
        self,
        skills: List[str],
        experience: List[Dict[str, Any]],
        education: List[Dict[str, Any]],
        text_length: int
    ) -> float:
        """
        Calculate confidence score (0-1) for resume assessment.
        
        Args:
            skills: Detected skills
            experience: Experience entries
            education: Education entries
            text_length: Length of resume text
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence_factors = []
        
        # Text length (longer resumes = more data = higher confidence)
        if text_length > 2000:
            confidence_factors.append(0.9)
        elif text_length > 1000:
            confidence_factors.append(0.7)
        elif text_length > 500:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Skills detected
        if len(skills) > 15:
            confidence_factors.append(0.9)
        elif len(skills) > 10:
            confidence_factors.append(0.7)
        elif len(skills) > 5:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Experience entries
        if len(experience) > 3:
            confidence_factors.append(0.8)
        elif len(experience) > 1:
            confidence_factors.append(0.6)
        elif len(experience) > 0:
            confidence_factors.append(0.4)
        else:
            confidence_factors.append(0.2)
        
        # Education entries
        if len(education) > 0:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.3)
        
        # Calculate average confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        return round(confidence, 3)
    
    def _generate_resume_summary(
        self,
        skills: List[str],
        experience_years: float,
        experience: List[Dict[str, Any]],
        education: List[Dict[str, Any]]
    ) -> str:
        """
        Generate human-readable summary of resume analysis.
        
        Args:
            skills: Detected skills
            experience_years: Years of experience
            experience: Experience entries
            education: Education entries
            
        Returns:
            Summary string
        """
        parts = []
        
        # Experience
        if experience_years > 0:
            parts.append(f"{experience_years} years of professional experience")
        
        # Skills
        if skills:
            skill_count = len(skills)
            top_skills = ", ".join(skills[:5])
            parts.append(f"{skill_count} technical skills detected including {top_skills}")
        
        # Recent positions
        if experience:
            recent_positions = [exp.get("title", "Unknown") for exp in experience[:2]]
            if recent_positions:
                parts.append(f"Recent roles: {', '.join(recent_positions)}")
        
        # Education
        if education:
            highest_degree = education[0].get("degree", "Degree")
            parts.append(f"Education: {highest_degree}")
        
        summary = ". ".join(parts) + "." if parts else "Resume parsed successfully."
        
        return summary
    
    def analyze_portfolio_website(self, url: str, user_id: UUID) -> SkillAssessment:
        """
        Scrape and analyze portfolio website.
        
        Extracts project descriptions, technologies used, and work samples
        from portfolio websites using BeautifulSoup4 for HTML parsing.
        
        Implements Requirements:
        - 13.7: Extract project descriptions, technologies, work samples from portfolio websites
        
        Args:
            url: Portfolio website URL
            user_id: User ID for associating the assessment
            
        Returns:
            SkillAssessment object with skill level (1-10) and project information
            
        Raises:
            ValueError: If URL is invalid or website cannot be accessed
            Exception: If scraping fails after retries
        """
        from bs4 import BeautifulSoup
        import re
        
        if not url:
            raise ValueError("Portfolio URL is required")
        
        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Fetch website content with retry logic
        try:
            html_content = self._fetch_website_with_retry(url)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch portfolio website {url}: {str(e)}")
            raise ValueError(f"Could not access portfolio website: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to fetch portfolio website {url}: {str(e)}")
            raise
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract portfolio data
        portfolio_data = self._extract_portfolio_data(soup, url)
        
        # Calculate skill level (1-10)
        skill_level = self._calculate_portfolio_skill_level(portfolio_data)
        
        # Calculate confidence score
        confidence_score = self._calculate_portfolio_confidence(portfolio_data)
        
        # Generate summary
        summary = self._generate_portfolio_summary(portfolio_data)
        
        # Create skill assessment
        assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.PORTFOLIO_WEBSITE,
            skill_level=skill_level,
            confidence_score=confidence_score,
            source_url=url,
            source_data={
                "projects_count": len(portfolio_data["projects"]),
                "technologies_count": len(portfolio_data["technologies"]),
                "work_samples_count": len(portfolio_data["work_samples"]),
                "has_about_section": portfolio_data["has_about_section"],
                "has_contact_info": portfolio_data["has_contact_info"],
                "projects": portfolio_data["projects"][:10],  # Store top 10 projects
                "work_samples": portfolio_data["work_samples"][:5]  # Store top 5 samples
            },
            detected_skills=portfolio_data["technologies"],
            experience_years=portfolio_data["estimated_experience_years"],
            proficiency_levels=portfolio_data["technology_proficiency"],
            analysis_summary=summary,
            extra_metadata={
                "total_text_length": portfolio_data["total_text_length"],
                "has_github_links": portfolio_data["has_github_links"],
                "has_live_demos": portfolio_data["has_live_demos"],
                "project_complexity_score": portfolio_data["project_complexity_score"],
                "portfolio_quality_score": portfolio_data["portfolio_quality_score"]
            }
        )
        
        # Save to database
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(f"Portfolio website analysis completed for user {user_id}: skill_level={skill_level}")
        return assessment
    
    @retry_with_exponential_backoff(
        max_retries=RetryConfig.WEB_SCRAPING_MAX_RETRIES,
        base_delay=RetryConfig.WEB_SCRAPING_BASE_DELAY,
        max_delay=RetryConfig.WEB_SCRAPING_MAX_DELAY,
        exceptions=(requests.exceptions.RequestException,)
    )
    def _fetch_website_with_retry(self, url: str, max_retries: int = 3) -> str:
        """
        Fetch website content with exponential backoff retry.
        
        Implements Requirement 13.12: API retry with exponential backoff
        
        Args:
            url: Website URL
            max_retries: Maximum number of retry attempts (deprecated, uses decorator config)
            
        Returns:
            HTML content as string
            
        Raises:
            ValueError: If website cannot be accessed after retries
        """
        # Set user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    
    def _extract_portfolio_data(self, soup: Any, url: str) -> Dict[str, Any]:
        """
        Extract project descriptions, technologies, and work samples from portfolio HTML.
        
        Implements Requirement 13.7: Extract project descriptions, technologies used, and work samples
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Portfolio website URL
            
        Returns:
            Dictionary with extracted portfolio data
        """
        import re
        
        # Initialize data structure
        portfolio_data = {
            "projects": [],
            "technologies": [],
            "work_samples": [],
            "has_about_section": False,
            "has_contact_info": False,
            "has_github_links": False,
            "has_live_demos": False,
            "total_text_length": 0,
            "estimated_experience_years": 0,
            "technology_proficiency": {},
            "project_complexity_score": 0,
            "portfolio_quality_score": 0
        }
        
        # Get all text content
        all_text = soup.get_text()
        portfolio_data["total_text_length"] = len(all_text)
        
        # Extract projects
        # Look for common project section patterns
        project_sections = []
        
        # Try to find project containers by common class/id names
        project_keywords = ['project', 'portfolio', 'work', 'case-study', 'showcase']
        for keyword in project_keywords:
            # Find by class
            project_sections.extend(soup.find_all(class_=re.compile(keyword, re.I)))
            # Find by id
            project_sections.extend(soup.find_all(id=re.compile(keyword, re.I)))
        
        # Also look for article, section tags that might contain projects
        project_sections.extend(soup.find_all(['article', 'section']))
        
        # Extract project information
        seen_projects = set()
        for section in project_sections:
            project_info = self._extract_project_info(section)
            if project_info and project_info["title"] not in seen_projects:
                portfolio_data["projects"].append(project_info)
                seen_projects.add(project_info["title"])
        
        # Extract technologies from entire page
        technologies = self._extract_technologies_from_html(soup)
        portfolio_data["technologies"] = list(set(technologies))[:20]  # Limit to top 20
        
        # Calculate technology proficiency based on frequency
        tech_counts = {}
        for tech in technologies:
            tech_counts[tech] = tech_counts.get(tech, 0) + 1
        
        max_count = max(tech_counts.values()) if tech_counts else 1
        portfolio_data["technology_proficiency"] = {
            tech: round(count / max_count, 3)
            for tech, count in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        }
        
        # Extract work samples (links to live demos, GitHub repos, etc.)
        portfolio_data["work_samples"] = self._extract_work_samples(soup)
        
        # Check for GitHub links
        github_links = soup.find_all('a', href=re.compile(r'github\.com', re.I))
        portfolio_data["has_github_links"] = len(github_links) > 0
        
        # Check for live demo links
        demo_keywords = ['demo', 'live', 'preview', 'visit', 'view']
        demo_links = []
        for keyword in demo_keywords:
            demo_links.extend(soup.find_all('a', string=re.compile(keyword, re.I)))
            demo_links.extend(soup.find_all('a', class_=re.compile(keyword, re.I)))
        portfolio_data["has_live_demos"] = len(demo_links) > 0
        
        # Check for about section
        about_keywords = ['about', 'bio', 'introduction', 'profile']
        for keyword in about_keywords:
            if soup.find(class_=re.compile(keyword, re.I)) or soup.find(id=re.compile(keyword, re.I)):
                portfolio_data["has_about_section"] = True
                break
        
        # Check for contact information
        contact_keywords = ['contact', 'email', 'reach', 'connect']
        for keyword in contact_keywords:
            if soup.find(class_=re.compile(keyword, re.I)) or soup.find(id=re.compile(keyword, re.I)):
                portfolio_data["has_contact_info"] = True
                break
        
        # Also check for email addresses
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', all_text):
            portfolio_data["has_contact_info"] = True
        
        # Calculate project complexity score
        portfolio_data["project_complexity_score"] = self._calculate_project_complexity(
            portfolio_data["projects"],
            portfolio_data["technologies"],
            portfolio_data["work_samples"]
        )
        
        # Calculate portfolio quality score
        portfolio_data["portfolio_quality_score"] = self._calculate_portfolio_quality(
            portfolio_data
        )
        
        # Estimate experience years based on project count and complexity
        project_count = len(portfolio_data["projects"])
        if project_count >= 10:
            portfolio_data["estimated_experience_years"] = 5.0
        elif project_count >= 6:
            portfolio_data["estimated_experience_years"] = 3.0
        elif project_count >= 3:
            portfolio_data["estimated_experience_years"] = 2.0
        elif project_count >= 1:
            portfolio_data["estimated_experience_years"] = 1.0
        else:
            portfolio_data["estimated_experience_years"] = 0.5
        
        return portfolio_data
    
    def _extract_project_info(self, section: Any) -> Optional[Dict[str, Any]]:
        """
        Extract project information from a section element.
        
        Args:
            section: BeautifulSoup element containing project info
            
        Returns:
            Dictionary with project title, description, and technologies, or None
        """
        import re
        
        # Try to find project title
        title = None
        for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            heading = section.find(heading_tag)
            if heading:
                title = heading.get_text().strip()
                break
        
        # If no heading found, try to find title in class or data attributes
        if not title:
            title_elem = section.find(class_=re.compile(r'title|name|heading', re.I))
            if title_elem:
                title = title_elem.get_text().strip()
        
        # Skip if no title or title is too short/generic
        if not title or len(title) < 3 or title.lower() in ['project', 'work', 'portfolio']:
            return None
        
        # Extract description
        description = ""
        desc_elem = section.find(class_=re.compile(r'description|summary|content|text', re.I))
        if desc_elem:
            description = desc_elem.get_text().strip()
        else:
            # Get all paragraph text
            paragraphs = section.find_all('p')
            if paragraphs:
                description = ' '.join(p.get_text().strip() for p in paragraphs[:3])  # First 3 paragraphs
        
        # Extract technologies mentioned in this project
        section_text = section.get_text()
        technologies = self._extract_technologies_from_text(section_text)
        
        # Extract links (GitHub, live demo, etc.)
        links = []
        for link in section.find_all('a', href=True):
            href = link.get('href')
            link_text = link.get_text().strip()
            if href and (href.startswith('http') or href.startswith('//')):
                links.append({
                    "url": href,
                    "text": link_text
                })
        
        return {
            "title": title[:200],  # Limit title length
            "description": description[:500],  # Limit description length
            "technologies": technologies,
            "links": links[:5]  # Limit to 5 links per project
        }
    
    def _extract_technologies_from_html(self, soup: Any) -> List[str]:
        """
        Extract technology keywords from HTML content.
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            List of detected technology keywords
        """
        # Get all text content
        text = soup.get_text()
        
        # Use existing method to extract technologies from text
        return self._extract_technologies_from_text(text)
    
    def _extract_work_samples(self, soup: Any) -> List[Dict[str, str]]:
        """
        Extract work sample links (GitHub repos, live demos, etc.).
        
        Args:
            soup: BeautifulSoup parsed HTML
            
        Returns:
            List of work sample dictionaries with url and type
        """
        import re
        
        work_samples = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            link_text = link.get_text().strip()
            
            if not href or not href.startswith(('http://', 'https://', '//')):
                continue
            
            # Categorize link type
            link_type = "other"
            if 'github.com' in href.lower():
                link_type = "github"
            elif any(keyword in link_text.lower() for keyword in ['demo', 'live', 'preview', 'visit']):
                link_type = "live_demo"
            elif any(keyword in href.lower() for keyword in ['demo', 'app', 'project']):
                link_type = "live_demo"
            
            if link_type != "other":
                work_samples.append({
                    "url": href,
                    "type": link_type,
                    "text": link_text[:100]  # Limit text length
                })
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_samples = []
        for sample in work_samples:
            if sample["url"] not in seen_urls:
                unique_samples.append(sample)
                seen_urls.add(sample["url"])
        
        return unique_samples[:20]  # Limit to 20 work samples
    
    def _calculate_project_complexity(
        self,
        projects: List[Dict[str, Any]],
        technologies: List[str],
        work_samples: List[Dict[str, str]]
    ) -> float:
        """
        Calculate project complexity score (0-10).
        
        Args:
            projects: List of project dictionaries
            technologies: List of technologies
            work_samples: List of work samples
            
        Returns:
            Complexity score between 0 and 10
        """
        score = 0.0
        
        # Project count factor (0-3 points)
        project_count = len(projects)
        score += min(3.0, project_count * 0.5)
        
        # Technology diversity factor (0-3 points)
        tech_count = len(technologies)
        score += min(3.0, tech_count * 0.2)
        
        # Work samples factor (0-2 points)
        sample_count = len(work_samples)
        score += min(2.0, sample_count * 0.2)
        
        # Project description quality factor (0-2 points)
        if projects:
            avg_desc_length = sum(len(p.get("description", "")) for p in projects) / len(projects)
            if avg_desc_length > 200:
                score += 2.0
            elif avg_desc_length > 100:
                score += 1.0
            elif avg_desc_length > 50:
                score += 0.5
        
        return round(min(10.0, score), 2)
    
    def _calculate_portfolio_quality(self, portfolio_data: Dict[str, Any]) -> float:
        """
        Calculate overall portfolio quality score (0-10).
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Quality score between 0 and 10
        """
        score = 0.0
        
        # Has about section (1 point)
        if portfolio_data["has_about_section"]:
            score += 1.0
        
        # Has contact info (1 point)
        if portfolio_data["has_contact_info"]:
            score += 1.0
        
        # Has GitHub links (1.5 points)
        if portfolio_data["has_github_links"]:
            score += 1.5
        
        # Has live demos (1.5 points)
        if portfolio_data["has_live_demos"]:
            score += 1.5
        
        # Content length (0-2 points)
        text_length = portfolio_data["total_text_length"]
        if text_length > 5000:
            score += 2.0
        elif text_length > 2000:
            score += 1.5
        elif text_length > 1000:
            score += 1.0
        elif text_length > 500:
            score += 0.5
        
        # Projects count (0-3 points)
        project_count = len(portfolio_data["projects"])
        score += min(3.0, project_count * 0.5)
        
        return round(min(10.0, score), 2)
    
    def _calculate_portfolio_skill_level(self, portfolio_data: Dict[str, Any]) -> int:
        """
        Calculate skill level (1-10) based on portfolio website analysis.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Skill level between 1 and 10
        """
        # Weighted scoring factors
        scores = {
            "project_complexity": portfolio_data["project_complexity_score"] * 0.35,
            "portfolio_quality": portfolio_data["portfolio_quality_score"] * 0.25,
            "technology_diversity": min(10, len(portfolio_data["technologies"]) * 0.5) * 0.20,
            "work_samples": min(10, len(portfolio_data["work_samples"]) * 0.5) * 0.20
        }
        
        # Calculate weighted average
        total_score = sum(scores.values())
        
        # Convert to 1-10 scale (ensure minimum of 1)
        skill_level = max(1, min(10, round(total_score)))
        
        return skill_level
    
    def _calculate_portfolio_confidence(self, portfolio_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score (0-1) for portfolio assessment.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence_factors = []
        
        # Content completeness
        if portfolio_data["total_text_length"] > 2000:
            confidence_factors.append(0.9)
        elif portfolio_data["total_text_length"] > 1000:
            confidence_factors.append(0.7)
        elif portfolio_data["total_text_length"] > 500:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Projects found
        project_count = len(portfolio_data["projects"])
        if project_count >= 5:
            confidence_factors.append(0.9)
        elif project_count >= 3:
            confidence_factors.append(0.7)
        elif project_count >= 1:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.2)
        
        # Technologies detected
        tech_count = len(portfolio_data["technologies"])
        if tech_count >= 10:
            confidence_factors.append(0.8)
        elif tech_count >= 5:
            confidence_factors.append(0.6)
        elif tech_count >= 2:
            confidence_factors.append(0.4)
        else:
            confidence_factors.append(0.2)
        
        # Work samples
        if len(portfolio_data["work_samples"]) >= 3:
            confidence_factors.append(0.8)
        elif len(portfolio_data["work_samples"]) >= 1:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
        
        # Calculate average confidence
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        return round(confidence, 3)
    
    def _generate_portfolio_summary(self, portfolio_data: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of portfolio website analysis.
        
        Args:
            portfolio_data: Portfolio data dictionary
            
        Returns:
            Summary string
        """
        parts = []
        
        # Projects
        project_count = len(portfolio_data["projects"])
        if project_count > 0:
            parts.append(f"{project_count} projects showcased")
        
        # Technologies
        tech_count = len(portfolio_data["technologies"])
        if tech_count > 0:
            top_techs = ", ".join(portfolio_data["technologies"][:5])
            parts.append(f"{tech_count} technologies including {top_techs}")
        
        # Work samples
        sample_count = len(portfolio_data["work_samples"])
        if sample_count > 0:
            github_count = sum(1 for s in portfolio_data["work_samples"] if s["type"] == "github")
            demo_count = sum(1 for s in portfolio_data["work_samples"] if s["type"] == "live_demo")
            if github_count > 0 and demo_count > 0:
                parts.append(f"{github_count} GitHub repos and {demo_count} live demos")
            elif github_count > 0:
                parts.append(f"{github_count} GitHub repositories")
            elif demo_count > 0:
                parts.append(f"{demo_count} live demos")
        
        # Quality indicators
        quality_indicators = []
        if portfolio_data["has_about_section"]:
            quality_indicators.append("about section")
        if portfolio_data["has_contact_info"]:
            quality_indicators.append("contact information")
        
        if quality_indicators:
            parts.append(f"Includes {' and '.join(quality_indicators)}")
        
        # Complexity and quality scores
        parts.append(
            f"Project complexity: {portfolio_data['project_complexity_score']:.1f}/10, "
            f"Portfolio quality: {portfolio_data['portfolio_quality_score']:.1f}/10"
        )
        
        summary = ". ".join(parts) + "." if parts else "Portfolio website analyzed successfully."
        
        return summary
    
    def combine_assessments(self, assessments: List[SkillAssessment], user_id: UUID) -> SkillAssessment:
        """
        Merge multiple skill assessments into unified score.
        
        Combines insights from multiple portfolio sources (GitHub, LinkedIn, resume,
        portfolio website, manual entry) and generates a unified skill assessment.
        Implements recency weighting where more recent assessments are weighted more heavily.
        
        Implements Requirements:
        - 1.12: Allow users to combine multiple input methods to build comprehensive profile
        - 13.9: Combine insights from multiple data sources
        - 13.10: Generate unified skill level score (1-10)
        
        Args:
            assessments: List of SkillAssessment objects from different sources
            user_id: User ID for associating the combined assessment
            
        Returns:
            Combined SkillAssessment object with unified skill level (1-10)
            
        Raises:
            ValueError: If assessments list is empty or contains invalid data
        """
        if not assessments:
            raise ValueError("At least one assessment is required for combination")
        
        # Validate all assessments belong to the same user
        for assessment in assessments:
            if assessment.user_id != user_id:
                raise ValueError(f"Assessment {assessment.id} does not belong to user {user_id}")
        
        # Sort assessments by creation date (most recent first) for recency weighting
        sorted_assessments = sorted(assessments, key=lambda a: a.created_at, reverse=True)
        
        # Calculate recency weights using exponential decay
        # Most recent: weight = 1.0
        # 1 month old: weight = 0.85
        # 3 months old: weight = 0.7
        # 6 months old: weight = 0.5
        # 12+ months old: weight = 0.3
        now = datetime.utcnow()
        weighted_assessments = []
        
        for assessment in sorted_assessments:
            days_old = (now - assessment.created_at).days
            
            if days_old < 30:  # Less than 1 month
                recency_weight = 1.0
            elif days_old < 90:  # 1-3 months
                recency_weight = 0.85
            elif days_old < 180:  # 3-6 months
                recency_weight = 0.7
            elif days_old < 365:  # 6-12 months
                recency_weight = 0.5
            else:  # 12+ months
                recency_weight = 0.3
            
            # Also weight by confidence score
            confidence_weight = assessment.confidence_score if assessment.confidence_score else 0.5
            
            # Combined weight = recency_weight * confidence_weight
            combined_weight = recency_weight * confidence_weight
            
            weighted_assessments.append({
                "assessment": assessment,
                "recency_weight": recency_weight,
                "confidence_weight": confidence_weight,
                "combined_weight": combined_weight
            })
        
        # Calculate weighted skill level
        total_weight = sum(wa["combined_weight"] for wa in weighted_assessments)
        
        if total_weight == 0:
            # Fallback to simple average if all weights are zero
            unified_skill_level = sum(a.skill_level for a in assessments) / len(assessments)
            total_weight = len(assessments)
        else:
            weighted_skill_sum = sum(
                wa["assessment"].skill_level * wa["combined_weight"]
                for wa in weighted_assessments
            )
            unified_skill_level = weighted_skill_sum / total_weight
        
        # Round to nearest integer and ensure 1-10 range
        unified_skill_level = max(1, min(10, round(unified_skill_level)))
        
        # Combine detected skills from all sources (deduplicate)
        all_skills = []
        for assessment in assessments:
            if assessment.detected_skills:
                all_skills.extend(assessment.detected_skills)
        
        # Deduplicate and sort by frequency
        skill_counts = {}
        for skill in all_skills:
            skill_lower = skill.lower()
            skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1
        
        # Get unique skills sorted by frequency, preserve original casing
        unique_skills_map = {}
        for skill in all_skills:
            skill_lower = skill.lower()
            if skill_lower not in unique_skills_map:
                unique_skills_map[skill_lower] = skill
        
        combined_skills = [
            unique_skills_map[skill_lower]
            for skill_lower, _ in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
        ][:30]  # Limit to top 30 skills
        
        # Combine proficiency levels (take maximum proficiency for each skill)
        combined_proficiency = {}
        for assessment in assessments:
            if assessment.proficiency_levels:
                for skill, proficiency in assessment.proficiency_levels.items():
                    skill_lower = skill.lower()
                    if skill_lower not in combined_proficiency or proficiency > combined_proficiency[skill_lower]:
                        combined_proficiency[skill_lower] = proficiency
        
        # Use original casing for proficiency levels
        final_proficiency = {}
        for skill_lower, proficiency in combined_proficiency.items():
            if skill_lower in unique_skills_map:
                final_proficiency[unique_skills_map[skill_lower]] = proficiency
        
        # Calculate combined experience years (take maximum)
        combined_experience_years = max(
            (a.experience_years for a in assessments if a.experience_years is not None),
            default=0.0
        )
        
        # Calculate combined confidence score (weighted average)
        combined_confidence = sum(
            wa["assessment"].confidence_score * wa["combined_weight"]
            for wa in weighted_assessments
            if wa["assessment"].confidence_score is not None
        ) / total_weight if total_weight > 0 else 0.5
        
        # Generate combined summary
        combined_summary = self._generate_combined_summary(
            assessments,
            weighted_assessments,
            unified_skill_level,
            combined_skills,
            combined_experience_years
        )
        
        # Collect source URLs and data
        source_urls = [a.source_url for a in assessments if a.source_url]
        source_breakdown = [
            {
                "source": a.source.value,
                "skill_level": a.skill_level,
                "confidence": a.confidence_score,
                "recency_weight": next(wa["recency_weight"] for wa in weighted_assessments if wa["assessment"].id == a.id),
                "combined_weight": next(wa["combined_weight"] for wa in weighted_assessments if wa["assessment"].id == a.id),
                "created_at": a.created_at.isoformat()
            }
            for a in assessments
        ]
        
        # Create combined skill assessment
        combined_assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.COMBINED,
            skill_level=unified_skill_level,
            confidence_score=round(combined_confidence, 3),
            source_url=", ".join(source_urls) if source_urls else None,
            source_data={
                "source_count": len(assessments),
                "sources": [a.source.value for a in assessments],
                "source_breakdown": source_breakdown,
                "assessment_ids": [str(a.id) for a in assessments]
            },
            detected_skills=combined_skills,
            experience_years=combined_experience_years,
            proficiency_levels=final_proficiency,
            analysis_summary=combined_summary,
            extra_metadata={
                "total_weight": round(total_weight, 3),
                "skill_diversity": len(combined_skills),
                "most_recent_source": sorted_assessments[0].source.value,
                "oldest_source": sorted_assessments[-1].source.value,
                "days_span": (sorted_assessments[0].created_at - sorted_assessments[-1].created_at).days,
                "weighted_skill_breakdown": {
                    a.source.value: {
                        "skill_level": a.skill_level,
                        "weight": next(wa["combined_weight"] for wa in weighted_assessments if wa["assessment"].id == a.id)
                    }
                    for a in assessments
                }
            }
        )
        
        # Save to database
        self.db.add(combined_assessment)
        self.db.commit()
        self.db.refresh(combined_assessment)
        
        logger.info(
            f"Combined assessment created for user {user_id}: "
            f"skill_level={unified_skill_level}, sources={len(assessments)}, "
            f"skills={len(combined_skills)}"
        )
        
        return combined_assessment
    
    def _generate_combined_summary(
        self,
        assessments: List[SkillAssessment],
        weighted_assessments: List[Dict[str, Any]],
        unified_skill_level: int,
        combined_skills: List[str],
        combined_experience_years: float
    ) -> str:
        """
        Generate human-readable summary of combined assessment.
        
        Args:
            assessments: List of source assessments
            weighted_assessments: List of weighted assessment data
            unified_skill_level: Calculated unified skill level
            combined_skills: Combined list of skills
            combined_experience_years: Combined experience years
            
        Returns:
            Summary string
        """
        parts = []
        
        # Overview
        source_names = [a.source.value.replace("_", " ").title() for a in assessments]
        parts.append(
            f"Combined assessment from {len(assessments)} sources: {', '.join(source_names)}"
        )
        
        # Unified skill level
        parts.append(f"Unified skill level: {unified_skill_level}/10")
        
        # Experience
        if combined_experience_years > 0:
            parts.append(f"{combined_experience_years} years of experience")
        
        # Skills
        if combined_skills:
            skill_count = len(combined_skills)
            top_skills = ", ".join(combined_skills[:5])
            parts.append(f"{skill_count} unique skills identified including {top_skills}")
        
        # Source breakdown with weights
        source_details = []
        for wa in weighted_assessments:
            assessment = wa["assessment"]
            source_name = assessment.source.value.replace("_", " ").title()
            weight_pct = round(wa["combined_weight"] * 100 / sum(w["combined_weight"] for w in weighted_assessments))
            source_details.append(
                f"{source_name} (skill level: {assessment.skill_level}, weight: {weight_pct}%)"
            )
        
        parts.append(f"Source contributions: {'; '.join(source_details)}")
        
        # Recency note
        most_recent = weighted_assessments[0]["assessment"]
        days_old = (datetime.utcnow() - most_recent.created_at).days
        if days_old < 7:
            recency_note = "Most recent data is from this week"
        elif days_old < 30:
            recency_note = "Most recent data is from this month"
        elif days_old < 90:
            recency_note = f"Most recent data is {days_old} days old"
        else:
            recency_note = f"Most recent data is {days_old} days old (consider updating)"
        
        parts.append(recency_note)
        
        summary = ". ".join(parts) + "."
        
        return summary

    def generate_vector_embedding(
        self,
        user_id: UUID,
        skill_level: int,
        learning_velocity: float,
        timezone: str,
        language: str,
        interest_area: str
    ) -> VectorEmbedding:
        """
        Generate vector embedding for matching algorithm.
        
        Creates a vector representation of the user based on skill level, learning velocity,
        timezone, language, and interest area. The embedding is stored in Pinecone for
        efficient similarity search during squad matching.
        
        Implements Requirement 2.1: Vector embedding generation based on skill level,
        learning velocity, timezone, and language.
        
        Args:
            user_id: User ID for associating the embedding
            skill_level: User's skill level (1-10)
            learning_velocity: User's learning velocity (tasks per day)
            timezone: User's timezone (IANA format, e.g., "America/New_York")
            language: User's preferred language (ISO 639-1 code, e.g., "en")
            interest_area: User's primary interest/guild area
            
        Returns:
            VectorEmbedding object with Pinecone ID and embedding metadata
            
        Raises:
            ValueError: If Pinecone is not configured or parameters are invalid
            Exception: If Pinecone operations fail
        """
        # Validate inputs
        if not 1 <= skill_level <= 10:
            raise ValueError(f"Skill level must be between 1 and 10, got {skill_level}")
        
        if learning_velocity < 0:
            raise ValueError(f"Learning velocity must be non-negative, got {learning_velocity}")
        
        if not timezone:
            raise ValueError("Timezone is required")
        
        if not language:
            raise ValueError("Language is required")
        
        if not interest_area:
            raise ValueError("Interest area is required")
        
        # Check Pinecone configuration
        if not settings.PINECONE_API_KEY:
            raise ValueError("Pinecone API key not configured")
        
        logger.info(f"Generating vector embedding for user {user_id}")
        
        # Initialize Sentence Transformer model (all-MiniLM-L6-v2 produces 384-dimensional embeddings)
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Normalize skill level to [0, 1]
        normalized_skill_level = skill_level / 10.0
        
        # Normalize learning velocity (cap at 10 tasks/day for normalization)
        normalized_velocity = min(learning_velocity / 10.0, 1.0)
        
        # Convert timezone to UTC offset in hours
        timezone_offset = self._get_timezone_offset(timezone)
        
        # Normalize timezone offset to [-1, 1] (assuming ±12 hours max)
        normalized_timezone = timezone_offset / 12.0
        
        # One-hot encode language (support top 20 languages)
        supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
            "ar", "hi", "nl", "pl", "tr", "sv", "no", "da", "fi", "el"
        ]
        language_vector = [1.0 if lang == language else 0.0 for lang in supported_languages]
        
        # Generate interest area embedding using Sentence Transformers
        interest_embedding = model.encode(interest_area, convert_to_numpy=True)
        
        # Combine all components into a single vector
        # Structure: [skill_level, velocity, timezone, language_one_hot (20 dims), interest_embedding (384 dims)]
        # Total: 1 + 1 + 1 + 20 + 384 = 407 dimensions
        # But we'll use 384 dimensions from the model and encode the metadata separately
        
        # Create a text representation that captures all features
        feature_text = (
            f"Skill level: {skill_level}/10. "
            f"Learning velocity: {learning_velocity:.2f} tasks per day. "
            f"Timezone: {timezone} (UTC{timezone_offset:+.1f}). "
            f"Language: {language}. "
            f"Interest area: {interest_area}."
        )
        
        # Generate embedding from feature text
        embedding_vector = model.encode(feature_text, convert_to_numpy=True)
        
        # Ensure embedding is 384 dimensions (model output)
        if len(embedding_vector) != 384:
            raise ValueError(f"Expected 384-dimensional embedding, got {len(embedding_vector)}")
        
        # Initialize Pinecone client
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Define index name
        index_name = "origin-user-embeddings"
        
        # Create index if it doesn't exist
        try:
            existing_indexes = pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if index_name not in index_names:
                logger.info(f"Creating Pinecone index: {index_name}")
                pc.create_index(
                    name=index_name,
                    dimension=384,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=settings.PINECONE_ENVIRONMENT or "us-east-1"
                    )
                )
                # Wait for index to be ready
                import time
                time.sleep(5)
        except Exception as e:
            logger.warning(f"Error checking/creating Pinecone index: {str(e)}")
            # Continue if index already exists
        
        # Get index
        index = pc.Index(index_name)
        
        # Generate unique Pinecone ID
        pinecone_id = f"user_{user_id}"
        
        # Prepare metadata for Pinecone
        metadata = {
            "user_id": str(user_id),
            "skill_level": skill_level,
            "learning_velocity": learning_velocity,
            "timezone": timezone,
            "timezone_offset": timezone_offset,
            "language": language,
            "interest_area": interest_area,
            "embedding_version": "v1",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Upsert vector to Pinecone
        try:
            index.upsert(
                vectors=[
                    {
                        "id": pinecone_id,
                        "values": embedding_vector.tolist(),
                        "metadata": metadata
                    }
                ]
            )
            logger.info(f"Successfully upserted vector to Pinecone: {pinecone_id}")
        except Exception as e:
            logger.error(f"Failed to upsert vector to Pinecone: {str(e)}")
            raise
        
        # Create VectorEmbedding record in database
        vector_embedding = VectorEmbedding(
            user_id=user_id,
            pinecone_id=pinecone_id,
            skill_level=skill_level,
            learning_velocity=learning_velocity,
            timezone_offset=timezone_offset,
            language_code=language,
            interest_area=interest_area,
            embedding_version="v1",
            dimensions=384,
            extra_metadata={
                "timezone": timezone,
                "feature_text": feature_text,
                "normalized_skill_level": normalized_skill_level,
                "normalized_velocity": normalized_velocity,
                "normalized_timezone": normalized_timezone
            }
        )
        
        # Save to database
        self.db.add(vector_embedding)
        self.db.commit()
        self.db.refresh(vector_embedding)
        
        logger.info(f"Vector embedding created for user {user_id}: {vector_embedding.id}")
        return vector_embedding
    
    def _get_timezone_offset(self, timezone: str) -> float:
        """
        Get UTC offset in hours for a given timezone.
        
        Args:
            timezone: IANA timezone string (e.g., "America/New_York")
            
        Returns:
            UTC offset in hours (e.g., -5.0 for EST)
        """
        try:
            from datetime import timezone as dt_timezone
            import pytz
            
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            offset_seconds = now.utcoffset().total_seconds()
            offset_hours = offset_seconds / 3600
            
            return offset_hours
        except Exception as e:
            logger.warning(f"Could not determine timezone offset for {timezone}: {str(e)}")
            # Default to UTC (0 offset)
            return 0.0

    def create_manual_assessment(
        self,
        skills: List[str],
        experience_years: float,
        proficiency_level: int,
        user_id: UUID
    ) -> SkillAssessment:
        """
        Create manual skill assessment from user-provided data.
        
        Implements Requirement 13.8: Accept structured input for skills,
        years of experience, and proficiency levels.
        
        Args:
            skills: List of manually entered skills
            experience_years: Years of experience
            proficiency_level: Self-assessed proficiency level (1-10)
            user_id: User ID for associating the assessment
            
        Returns:
            SkillAssessment object with manual entry data
            
        Raises:
            ValueError: If proficiency_level is out of range
        """
        if not 1 <= proficiency_level <= 10:
            raise ValueError(f"Proficiency level must be between 1 and 10, got: {proficiency_level}")
        
        # Use proficiency level as skill level
        skill_level = proficiency_level
        
        # Calculate confidence score based on amount of information provided
        confidence_score = 0.5  # Base confidence for manual entry
        if skills and len(skills) >= 3:
            confidence_score += 0.2
        if experience_years > 0:
            confidence_score += 0.2
        confidence_score = min(1.0, confidence_score)
        
        # Create proficiency levels dict (all skills at same level)
        proficiency_levels = {skill: proficiency_level for skill in skills}
        
        # Generate summary
        skills_str = ", ".join(skills[:5])
        if len(skills) > 5:
            skills_str += f" and {len(skills) - 5} more"
        
        summary = (
            f"Manual skill entry: {len(skills)} skills provided "
            f"({skills_str}). "
            f"Self-assessed proficiency level: {proficiency_level}/10. "
            f"Experience: {experience_years} years."
        )
        
        # Create skill assessment
        assessment = SkillAssessment(
            user_id=user_id,
            source=AssessmentSource.MANUAL,
            skill_level=skill_level,
            confidence_score=confidence_score,
            source_url=None,
            source_data={
                "manual_entry": True,
                "skills_count": len(skills),
                "experience_years": experience_years,
                "proficiency_level": proficiency_level
            },
            detected_skills=skills,
            experience_years=experience_years,
            proficiency_levels=proficiency_levels,
            analysis_summary=summary,
            extra_metadata={
                "entry_method": "manual",
                "confidence_note": "Based on self-assessment"
            }
        )
        
        # Save to database
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        
        logger.info(f"Manual assessment created for user {user_id}: skill_level={skill_level}")
        return assessment
