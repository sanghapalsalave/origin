"""
Tests for resume parsing functionality.

Tests Requirements:
- 13.5: Resume format support (PDF, DOCX, TXT)
- 13.6: NLP skill extraction
"""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch
from app.services.resume_parser import ResumeParser
from app.services.portfolio_analysis_service import PortfolioAnalysisService
from app.models.skill_assessment import SkillAssessment, AssessmentSource
from uuid import uuid4


class TestResumeParser:
    """Test suite for ResumeParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create ResumeParser instance."""
        return ResumeParser()
    
    @pytest.fixture
    def sample_resume_text(self):
        """Sample resume text for testing."""
        return """
        John Doe
        john.doe@email.com | (555) 123-4567
        linkedin.com/in/johndoe | github.com/johndoe
        
        PROFESSIONAL EXPERIENCE
        
        Senior Software Engineer
        Tech Company Inc.
        2020 - Present
        - Developed scalable web applications using Python, Django, and React
        - Led team of 5 engineers in building microservices architecture
        - Implemented CI/CD pipelines with Docker and Kubernetes
        - Expert in AWS cloud services and PostgreSQL databases
        
        Software Engineer
        Startup LLC
        2018 - 2020
        - Built REST APIs using Node.js and Express
        - Worked with MongoDB and Redis for data storage
        - Proficient in JavaScript, TypeScript, and Vue.js
        
        Junior Developer
        Small Company
        2016 - 2018
        - Developed web applications using HTML, CSS, and JavaScript
        - Basic experience with SQL and MySQL
        
        EDUCATION
        
        Bachelor of Science in Computer Science
        University of Technology
        2016
        
        SKILLS
        
        Programming Languages: Python, JavaScript, TypeScript, Java
        Frameworks: Django, React, Node.js, Express, Vue.js
        Databases: PostgreSQL, MongoDB, Redis, MySQL
        Cloud: AWS, Docker, Kubernetes
        Tools: Git, Jenkins, CI/CD
        """
    
    def test_extract_text_from_txt(self, parser, sample_resume_text):
        """Test extracting text from TXT file."""
        file_content = sample_resume_text.encode('utf-8')
        text = parser._extract_text_from_txt(file_content)
        
        assert len(text) > 0
        assert "John Doe" in text
        assert "Software Engineer" in text
    
    def test_extract_contact_info(self, parser, sample_resume_text):
        """Test extracting contact information."""
        contact_info = parser._extract_contact_info(sample_resume_text)
        
        assert contact_info["email"] == "john.doe@email.com"
        assert contact_info["phone"] is not None
        assert "linkedin.com" in contact_info["linkedin"]
        assert "github.com" in contact_info["github"]
    
    def test_extract_skills_nlp(self, parser, sample_resume_text):
        """Test NLP skill extraction."""
        skills = parser._extract_skills_nlp(sample_resume_text)
        
        # Should detect various skills
        assert len(skills) > 0
        
        # Check for specific skills mentioned in resume
        skills_lower = [s.lower() for s in skills]
        assert any("python" in s for s in skills_lower)
        assert any("javascript" in s for s in skills_lower)
        assert any("react" in s for s in skills_lower)
        assert any("docker" in s for s in skills_lower)
    
    def test_extract_experience(self, parser, sample_resume_text):
        """Test extracting work experience."""
        experience = parser._extract_experience(sample_resume_text)
        
        # Should find multiple experience entries
        assert len(experience) >= 2
        
        # Check first entry
        if experience:
            first_exp = experience[0]
            assert "title" in first_exp
            assert "dates" in first_exp
    
    def test_extract_education(self, parser, sample_resume_text):
        """Test extracting education."""
        education = parser._extract_education(sample_resume_text)
        
        # Should find at least one education entry
        assert len(education) >= 1
        
        if education:
            first_edu = education[0]
            assert "degree" in first_edu
            assert "bachelor" in first_edu["degree"].lower() or "computer science" in first_edu["degree"].lower()
    
    def test_calculate_skill_proficiency(self, parser, sample_resume_text):
        """Test calculating skill proficiency levels."""
        skills = ["Python", "JavaScript", "Docker"]
        proficiency = parser._calculate_skill_proficiency(sample_resume_text, skills)
        
        assert len(proficiency) == len(skills)
        
        # Python is mentioned as "Expert" so should have reasonable proficiency
        if "Python" in proficiency:
            assert proficiency["Python"] >= 0.5  # Adjusted threshold
        
        # All proficiency values should be between 0 and 1
        for skill, level in proficiency.items():
            assert 0.0 <= level <= 1.0
    
    def test_estimate_experience_years(self, parser, sample_resume_text):
        """Test estimating years of experience."""
        experience = parser._extract_experience(sample_resume_text)
        years = parser._estimate_experience_years(experience, sample_resume_text)
        
        # Should estimate reasonable years (resume shows 2016-present)
        assert years > 0
        assert years <= 50  # Reasonable cap
    
    def test_parse_resume_txt(self, parser, sample_resume_text):
        """Test full resume parsing for TXT format."""
        file_content = sample_resume_text.encode('utf-8')
        result = parser.parse_resume(file_content, 'txt')
        
        assert "text" in result
        assert "skills" in result
        assert "experience" in result
        assert "education" in result
        assert "contact_info" in result
        assert "proficiency_levels" in result
        assert "experience_years" in result
        
        # Verify data quality
        assert len(result["skills"]) > 0
        assert result["experience_years"] > 0
    
    def test_parse_resume_invalid_type(self, parser):
        """Test parsing with invalid file type."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse_resume(b"test content", 'invalid')
    
    def test_parse_resume_empty_content(self, parser):
        """Test parsing with empty content."""
        with pytest.raises(ValueError, match="empty or too short"):
            parser.parse_resume(b"", 'txt')
    
    def test_normalize_skill_name(self, parser):
        """Test skill name normalization."""
        assert parser._normalize_skill_name("reactjs") == "React"
        assert parser._normalize_skill_name("nodejs") == "Node.js"
        assert parser._normalize_skill_name("aws") == "Aws"  # Title case default
        assert parser._normalize_skill_name("machine learning") == "Machine Learning"


class TestPortfolioAnalysisServiceResume:
    """Test suite for resume parsing in PortfolioAnalysisService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Create PortfolioAnalysisService instance."""
        return PortfolioAnalysisService(mock_db)
    
    @pytest.fixture
    def sample_resume_text(self):
        """Sample resume text."""
        return """
        Jane Smith
        jane.smith@email.com
        
        EXPERIENCE
        Senior Data Scientist - AI Corp - 2019-Present
        Developed machine learning models using Python, TensorFlow, and PyTorch
        Expert in deep learning and natural language processing
        
        Data Analyst - Data Inc - 2017-2019
        Analyzed data using SQL, Python, and R
        Proficient in data visualization with Matplotlib and Seaborn
        
        EDUCATION
        Master of Science in Data Science - 2017
        
        SKILLS
        Python, TensorFlow, PyTorch, Machine Learning, Deep Learning, NLP
        SQL, PostgreSQL, Pandas, NumPy, Scikit-learn
        """
    
    def test_parse_resume_creates_assessment(self, service, mock_db, sample_resume_text):
        """Test that parse_resume creates a SkillAssessment."""
        user_id = uuid4()
        file_content = sample_resume_text.encode('utf-8')
        
        assessment = service.parse_resume(file_content, 'txt', user_id)
        
        # Verify assessment was created
        assert isinstance(assessment, SkillAssessment)
        assert assessment.user_id == user_id
        assert assessment.source == AssessmentSource.RESUME
        assert 1 <= assessment.skill_level <= 10
        assert 0.0 <= assessment.confidence_score <= 1.0
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_parse_resume_detects_skills(self, service, mock_db, sample_resume_text):
        """Test that skills are properly detected."""
        user_id = uuid4()
        file_content = sample_resume_text.encode('utf-8')
        
        assessment = service.parse_resume(file_content, 'txt', user_id)
        
        # Should detect multiple skills
        assert len(assessment.detected_skills) > 0
        
        # Check for specific skills
        skills_lower = [s.lower() for s in assessment.detected_skills]
        assert any("python" in s for s in skills_lower)
        assert any("machine learning" in s or "ml" in s for s in skills_lower)
    
    def test_parse_resume_calculates_experience(self, service, mock_db, sample_resume_text):
        """Test that experience years are calculated."""
        user_id = uuid4()
        file_content = sample_resume_text.encode('utf-8')
        
        assessment = service.parse_resume(file_content, 'txt', user_id)
        
        # Should have experience years
        assert assessment.experience_years is not None
        assert assessment.experience_years > 0
    
    def test_parse_resume_has_proficiency_levels(self, service, mock_db, sample_resume_text):
        """Test that proficiency levels are calculated."""
        user_id = uuid4()
        file_content = sample_resume_text.encode('utf-8')
        
        assessment = service.parse_resume(file_content, 'txt', user_id)
        
        # Should have proficiency levels
        assert assessment.proficiency_levels is not None
        assert len(assessment.proficiency_levels) > 0
        
        # All proficiency values should be valid
        for skill, level in assessment.proficiency_levels.items():
            assert 0.0 <= level <= 1.0
    
    def test_parse_resume_generates_summary(self, service, mock_db, sample_resume_text):
        """Test that a summary is generated."""
        user_id = uuid4()
        file_content = sample_resume_text.encode('utf-8')
        
        assessment = service.parse_resume(file_content, 'txt', user_id)
        
        # Should have a summary
        assert assessment.analysis_summary is not None
        assert len(assessment.analysis_summary) > 0
    
    def test_calculate_resume_skill_level(self, service):
        """Test skill level calculation."""
        skills = ["Python", "JavaScript", "React", "Docker", "AWS"]
        experience_years = 5.0
        education = [{"degree": "Bachelor of Science in Computer Science"}]
        proficiency = {"Python": 0.9, "JavaScript": 0.8, "React": 0.7, "Docker": 0.6, "AWS": 0.5}
        
        skill_level = service._calculate_resume_skill_level(
            skills, experience_years, education, proficiency
        )
        
        assert 1 <= skill_level <= 10
        # With 5 years experience and good skills, should be mid-to-high level
        assert skill_level >= 5
    
    def test_calculate_resume_confidence(self, service):
        """Test confidence score calculation."""
        skills = ["Python", "JavaScript", "React"]
        experience = [{"title": "Engineer", "dates": "2020-2023"}]
        education = [{"degree": "BS Computer Science"}]
        text_length = 2000
        
        confidence = service._calculate_resume_confidence(
            skills, experience, education, text_length
        )
        
        assert 0.0 <= confidence <= 1.0
        # With good data, confidence should be reasonable
        assert confidence >= 0.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
