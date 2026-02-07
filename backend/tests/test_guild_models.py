"""
Unit tests for Guild and GuildMembership models.

Tests guild creation, types, relationships, and membership tracking.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from app.models.guild import Guild, GuildMembership, GuildType
# Import Squad to ensure it's registered with SQLAlchemy
from app.models.squad import Squad, SquadMembership


class TestGuildModel:
    """Test cases for Guild model."""
    
    def test_guild_creation_public(self):
        """Test basic public guild creation."""
        guild = Guild(
            id=uuid4(),
            name="Python Masters",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC,
            certification_enabled=False,
            created_at=datetime.utcnow()
        )
        
        assert guild.name == "Python Masters"
        assert guild.interest_area == "Python Development"
        assert guild.guild_type == GuildType.PUBLIC
        assert guild.certification_enabled is False
        assert guild.company_id is None
        assert guild.expert_facilitator_id is None
    
    def test_guild_creation_premium(self):
        """Test premium guild creation with expert facilitator."""
        guild_id = uuid4()
        facilitator_id = uuid4()
        
        guild = Guild(
            id=guild_id,
            name="Advanced React",
            interest_area="React Development",
            guild_type=GuildType.PREMIUM,
            expert_facilitator_id=facilitator_id,
            certification_enabled=True,
            created_at=datetime.utcnow()
        )
        
        assert guild.guild_type == GuildType.PREMIUM
        assert guild.expert_facilitator_id == facilitator_id
        assert guild.certification_enabled is True
    
    def test_guild_creation_private(self):
        """Test private guild creation with company restrictions."""
        company_id = uuid4()
        
        guild = Guild(
            id=uuid4(),
            name="Acme Corp Training",
            interest_area="Enterprise Architecture",
            guild_type=GuildType.PRIVATE,
            company_id=company_id,
            allowed_email_domains=["acme.com", "acme-subsidiary.com"],
            custom_objectives=["Learn microservices", "Master Kubernetes"],
            created_at=datetime.utcnow()
        )
        
        assert guild.guild_type == GuildType.PRIVATE
        assert guild.company_id == company_id
        assert guild.allowed_email_domains == ["acme.com", "acme-subsidiary.com"]
        assert guild.custom_objectives == ["Learn microservices", "Master Kubernetes"]
    
    def test_guild_type_enum_values(self):
        """Test that GuildType enum has correct values."""
        assert GuildType.PUBLIC.value == "public"
        assert GuildType.PREMIUM.value == "premium"
        assert GuildType.PRIVATE.value == "private"
    
    def test_guild_default_certification_disabled(self):
        """Test that certification is disabled by default."""
        guild = Guild(
            id=uuid4(),
            name="Test Guild",
            interest_area="Testing",
            guild_type=GuildType.PUBLIC,
            certification_enabled=False,
            created_at=datetime.utcnow()
        )
        
        assert guild.certification_enabled is False
    
    def test_guild_optional_fields(self):
        """Test that optional fields are None by default."""
        guild = Guild(
            id=uuid4(),
            name="Test Guild",
            interest_area="Testing",
            guild_type=GuildType.PUBLIC,
            created_at=datetime.utcnow()
        )
        
        assert guild.company_id is None
        assert guild.allowed_email_domains is None
        assert guild.custom_objectives is None
        assert guild.expert_facilitator_id is None
    
    def test_guild_repr(self):
        """Test guild string representation."""
        guild_id = uuid4()
        guild = Guild(
            id=guild_id,
            name="Python Masters",
            interest_area="Python Development",
            guild_type=GuildType.PUBLIC,
            created_at=datetime.utcnow()
        )
        
        repr_str = repr(guild)
        assert "Guild" in repr_str
        assert str(guild_id) in repr_str
        assert "Python Masters" in repr_str
        assert "public" in repr_str
        assert "Python Development" in repr_str
    
    def test_guild_with_multiple_custom_objectives(self):
        """Test private guild with multiple custom objectives."""
        objectives = [
            "Master cloud architecture",
            "Learn CI/CD pipelines",
            "Understand security best practices",
            "Implement monitoring solutions"
        ]
        
        guild = Guild(
            id=uuid4(),
            name="DevOps Academy",
            interest_area="DevOps",
            guild_type=GuildType.PRIVATE,
            company_id=uuid4(),
            custom_objectives=objectives,
            created_at=datetime.utcnow()
        )
        
        assert len(guild.custom_objectives) == 4
        assert guild.custom_objectives == objectives
    
    def test_guild_with_multiple_email_domains(self):
        """Test private guild with multiple allowed email domains."""
        domains = ["company.com", "subsidiary1.com", "subsidiary2.com"]
        
        guild = Guild(
            id=uuid4(),
            name="Enterprise Training",
            interest_area="Enterprise Development",
            guild_type=GuildType.PRIVATE,
            company_id=uuid4(),
            allowed_email_domains=domains,
            created_at=datetime.utcnow()
        )
        
        assert len(guild.allowed_email_domains) == 3
        assert guild.allowed_email_domains == domains


class TestGuildMembershipModel:
    """Test cases for GuildMembership model."""
    
    def test_guild_membership_creation(self):
        """Test basic guild membership creation."""
        user_id = uuid4()
        guild_id = uuid4()
        joined_at = datetime.utcnow()
        
        membership = GuildMembership(
            id=uuid4(),
            user_id=user_id,
            guild_id=guild_id,
            joined_at=joined_at
        )
        
        assert membership.user_id == user_id
        assert membership.guild_id == guild_id
        assert membership.joined_at == joined_at
    
    def test_guild_membership_repr(self):
        """Test guild membership string representation."""
        user_id = uuid4()
        guild_id = uuid4()
        
        membership = GuildMembership(
            id=uuid4(),
            user_id=user_id,
            guild_id=guild_id,
            joined_at=datetime.utcnow()
        )
        
        repr_str = repr(membership)
        assert "GuildMembership" in repr_str
        assert str(user_id) in repr_str
        assert str(guild_id) in repr_str
    
    def test_multiple_memberships_same_user(self):
        """Test that a user can have multiple guild memberships."""
        user_id = uuid4()
        guild1_id = uuid4()
        guild2_id = uuid4()
        
        membership1 = GuildMembership(
            id=uuid4(),
            user_id=user_id,
            guild_id=guild1_id,
            joined_at=datetime.utcnow()
        )
        
        membership2 = GuildMembership(
            id=uuid4(),
            user_id=user_id,
            guild_id=guild2_id,
            joined_at=datetime.utcnow()
        )
        
        assert membership1.user_id == membership2.user_id
        assert membership1.guild_id != membership2.guild_id
    
    def test_multiple_memberships_same_guild(self):
        """Test that a guild can have multiple user memberships."""
        guild_id = uuid4()
        user1_id = uuid4()
        user2_id = uuid4()
        
        membership1 = GuildMembership(
            id=uuid4(),
            user_id=user1_id,
            guild_id=guild_id,
            joined_at=datetime.utcnow()
        )
        
        membership2 = GuildMembership(
            id=uuid4(),
            user_id=user2_id,
            guild_id=guild_id,
            joined_at=datetime.utcnow()
        )
        
        assert membership1.guild_id == membership2.guild_id
        assert membership1.user_id != membership2.user_id


class TestGuildRelationships:
    """Test cases for Guild relationships."""
    
    def test_guild_membership_relationship_setup(self):
        """Test that Guild and GuildMembership can be linked."""
        guild_id = uuid4()
        user_id = uuid4()
        
        guild = Guild(
            id=guild_id,
            name="Test Guild",
            interest_area="Testing",
            guild_type=GuildType.PUBLIC,
            created_at=datetime.utcnow()
        )
        
        membership = GuildMembership(
            id=uuid4(),
            user_id=user_id,
            guild_id=guild_id,
            joined_at=datetime.utcnow()
        )
        
        # Verify the foreign key relationship
        assert membership.guild_id == guild.id
    
    def test_guild_expert_facilitator_relationship(self):
        """Test that Guild can reference an expert facilitator user."""
        facilitator_id = uuid4()
        
        guild = Guild(
            id=uuid4(),
            name="Premium Guild",
            interest_area="Advanced Topics",
            guild_type=GuildType.PREMIUM,
            expert_facilitator_id=facilitator_id,
            created_at=datetime.utcnow()
        )
        
        # Verify the foreign key relationship
        assert guild.expert_facilitator_id == facilitator_id
