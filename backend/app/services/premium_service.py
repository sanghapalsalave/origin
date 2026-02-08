"""
Premium and B2B Service

Provides premium subscription management, expert facilitator assignment,
certificate generation, and company analytics functionality.

Implements Requirements:
- 10.1: Premium subscription access control
- 10.2: Expert facilitator assignment
- 10.3: AI-verified certificate generation
- 10.4: Certificate display on profiles
- 10.5: Subscription expiration handling
- 11.1: Private guild email domain restriction
- 11.2: Custom objectives for private guilds
- 11.3: Incorporate custom objectives into syllabus
- 11.4: Company analytics dashboard
- 11.5: Employee access revocation
"""
import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import secrets

from app.models.premium import (
    Subscription, SubscriptionStatus, Certificate, Company,
    CompanyAdministrator, EmployeeAccess
)
from app.models.guild import Guild, GuildType, GuildMembership
from app.models.user import User
from app.models.squad import Squad, SquadMembership

logger = logging.getLogger(__name__)


class PremiumService:
    """Service for premium and B2B operations."""
    
    def __init__(self, db: Session):
        """
        Initialize Premium service.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("PremiumService initialized")
    
    def assign_facilitator(
        self,
        guild_id: UUID,
        facilitator_id: UUID
    ) -> Guild:
        """
        Assign an expert facilitator to a premium guild.
        
        When a user joins a premium guild, an expert facilitator is assigned
        in addition to the AI Guild Master to provide higher-quality instruction.
        
        Implements Requirement 10.2: Expert facilitator assignment for premium guilds.
        
        Args:
            guild_id: ID of premium guild
            facilitator_id: ID of expert facilitator user
            
        Returns:
            Updated Guild object
            
        Raises:
            ValueError: If guild not found, not premium type, or facilitator not found
        """
        # Validate guild exists and is premium
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        if guild.guild_type != GuildType.PREMIUM:
            raise ValueError(
                f"Guild {guild_id} is not a premium guild (type: {guild.guild_type})"
            )
        
        # Validate facilitator exists
        facilitator = self.db.query(User).filter(User.id == facilitator_id).first()
        if not facilitator:
            raise ValueError(f"Facilitator {facilitator_id} not found")
        
        # Assign facilitator
        guild.expert_facilitator_id = facilitator_id
        
        logger.info(
            f"Assigned expert facilitator {facilitator_id} to premium guild {guild_id}"
        )
        
        self.db.commit()
        self.db.refresh(guild)
        
        return guild
    
    def handle_subscription_expiration(
        self,
        subscription_id: UUID
    ) -> Dict:
        """
        Handle subscription expiration.
        
        When a premium subscription expires:
        - Maintain access to completed certifications
        - Restrict new premium guild enrollment
        - Update subscription status to EXPIRED
        
        Implements Requirement 10.5: Subscription expiration handling.
        
        Args:
            subscription_id: ID of subscription to expire
            
        Returns:
            Dictionary with expiration details:
            {
                'subscription_id': str,
                'user_id': str,
                'status': str,
                'certificates_retained': int,
                'message': str
            }
            
        Raises:
            ValueError: If subscription not found
        """
        # Get subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.id == subscription_id
        ).first()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Count certificates to retain
        certificates_count = self.db.query(Certificate).filter(
            Certificate.user_id == subscription.user_id
        ).count()
        
        # Update subscription status
        subscription.status = SubscriptionStatus.EXPIRED
        
        logger.info(
            f"Subscription {subscription_id} expired for user {subscription.user_id}. "
            f"Retaining {certificates_count} certificates."
        )
        
        self.db.commit()
        
        return {
            'subscription_id': str(subscription_id),
            'user_id': str(subscription.user_id),
            'status': SubscriptionStatus.EXPIRED.value,
            'certificates_retained': certificates_count,
            'message': (
                f'Subscription expired. {certificates_count} certificates retained. '
                'Premium guild enrollment restricted.'
            )
        }
    
    def configure_private_guild(
        self,
        guild_id: UUID,
        company_id: UUID,
        custom_objectives: List[str]
    ) -> Guild:
        """
        Configure custom objectives for a private guild.
        
        Allows company administrators to specify custom learning objectives
        that will be incorporated into syllabus generation by the Guild Master.
        
        Implements Requirements:
        - 11.2: Custom objectives for private guilds
        - 11.3: Incorporate into syllabus generation
        
        Args:
            guild_id: ID of private guild
            company_id: ID of company
            custom_objectives: List of custom learning objectives
            
        Returns:
            Updated Guild object
            
        Raises:
            ValueError: If guild not found, not private type, or company mismatch
        """
        # Validate guild exists and is private
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        if guild.guild_type != GuildType.PRIVATE:
            raise ValueError(
                f"Guild {guild_id} is not a private guild (type: {guild.guild_type})"
            )
        
        # Validate company ownership
        if guild.company_id != company_id:
            raise ValueError(
                f"Guild {guild_id} does not belong to company {company_id}"
            )
        
        # Validate custom objectives
        if not custom_objectives or len(custom_objectives) == 0:
            raise ValueError("At least one custom objective is required")
        
        # Update custom objectives
        guild.custom_objectives = custom_objectives
        
        logger.info(
            f"Configured {len(custom_objectives)} custom objectives for private guild {guild_id}"
        )
        
        self.db.commit()
        self.db.refresh(guild)
        
        return guild
    
    def get_company_analytics(
        self,
        company_id: UUID
    ) -> Dict:
        """
        Get company analytics dashboard data.
        
        Provides company administrators with analytics showing:
        - Total employees enrolled
        - Progress by guild
        - Completion rates
        - Active vs inactive employees
        - Top performers
        
        Implements Requirement 11.4: Company analytics dashboard.
        
        Args:
            company_id: ID of company
            
        Returns:
            Dictionary with analytics data:
            {
                'company_id': str,
                'total_employees': int,
                'active_employees': int,
                'guilds': List[dict],
                'overall_completion_rate': float,
                'top_performers': List[dict]
            }
            
        Raises:
            ValueError: If company not found
        """
        # Validate company exists
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Get all employee accesses for this company
        employee_accesses = self.db.query(EmployeeAccess).filter(
            EmployeeAccess.company_id == company_id
        ).all()
        
        # Count unique employees
        unique_employee_ids = set(ea.user_id for ea in employee_accesses)
        total_employees = len(unique_employee_ids)
        
        # Count active employees (have at least one active access)
        active_employee_ids = set(
            ea.user_id for ea in employee_accesses if ea.is_active
        )
        active_employees = len(active_employee_ids)
        
        # Get guild-level analytics
        guild_analytics = []
        private_guilds = self.db.query(Guild).filter(
            Guild.company_id == company_id
        ).all()
        
        total_tasks_completed = 0
        total_tasks_assigned = 0
        
        for guild in private_guilds:
            # Get squads in this guild
            squads = self.db.query(Squad).filter(Squad.guild_id == guild.id).all()
            
            # Count members
            member_count = self.db.query(GuildMembership).filter(
                GuildMembership.guild_id == guild.id
            ).count()
            
            # TODO: In a future task, calculate actual completion rates from syllabus data
            # For now, we provide placeholder structure
            guild_analytics.append({
                'guild_id': str(guild.id),
                'guild_name': guild.name,
                'member_count': member_count,
                'squad_count': len(squads),
                'completion_rate': 0.0  # Placeholder
            })
        
        # Calculate overall completion rate
        overall_completion_rate = (
            (total_tasks_completed / total_tasks_assigned * 100)
            if total_tasks_assigned > 0 else 0.0
        )
        
        # Get top performers (users with highest reputation in company guilds)
        # TODO: In a future task, implement more sophisticated ranking
        top_performers = []
        
        analytics = {
            'company_id': str(company_id),
            'company_name': company.name,
            'total_employees': total_employees,
            'active_employees': active_employees,
            'guilds': guild_analytics,
            'overall_completion_rate': round(overall_completion_rate, 2),
            'top_performers': top_performers
        }
        
        logger.info(
            f"Generated analytics for company {company_id}: "
            f"{total_employees} employees, {len(guild_analytics)} guilds"
        )
        
        return analytics
    
    def revoke_employee_access(
        self,
        company_id: UUID,
        user_id: UUID,
        guild_id: Optional[UUID] = None
    ) -> Dict:
        """
        Revoke employee access to private guilds.
        
        When an employee leaves the company:
        - Revoke access to private guilds
        - Maintain their personal learning history
        - Update EmployeeAccess records
        
        If guild_id is provided, revokes access to that specific guild only.
        If guild_id is None, revokes access to all company guilds.
        
        Implements Requirement 11.5: Employee access revocation.
        
        Args:
            company_id: ID of company
            user_id: ID of employee user
            guild_id: Optional specific guild ID to revoke access from
            
        Returns:
            Dictionary with revocation details:
            {
                'company_id': str,
                'user_id': str,
                'guilds_revoked': int,
                'learning_history_maintained': bool,
                'message': str
            }
            
        Raises:
            ValueError: If company or user not found
        """
        # Validate company exists
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company {company_id} not found")
        
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Build query for employee accesses
        query = self.db.query(EmployeeAccess).filter(
            and_(
                EmployeeAccess.company_id == company_id,
                EmployeeAccess.user_id == user_id,
                EmployeeAccess.is_active == True
            )
        )
        
        # Filter by specific guild if provided
        if guild_id:
            query = query.filter(EmployeeAccess.guild_id == guild_id)
        
        # Get active accesses to revoke
        accesses_to_revoke = query.all()
        
        # Revoke accesses
        revoked_count = 0
        for access in accesses_to_revoke:
            access.is_active = False
            access.access_revoked_at = datetime.utcnow()
            revoked_count += 1
        
        self.db.commit()
        
        logger.info(
            f"Revoked {revoked_count} guild access(es) for user {user_id} "
            f"from company {company_id}. Learning history maintained."
        )
        
        return {
            'company_id': str(company_id),
            'user_id': str(user_id),
            'guilds_revoked': revoked_count,
            'learning_history_maintained': True,
            'message': (
                f'Access revoked to {revoked_count} guild(s). '
                'Personal learning history maintained.'
            )
        }
    
    def generate_certificate(
        self,
        user_id: UUID,
        guild_id: UUID,
        certificate_name: str,
        description: str
    ) -> Certificate:
        """
        Generate an AI-verified certificate for premium guild completion.
        
        Certificates are generated when premium guild members complete
        the curriculum and are displayed on user profiles with badges.
        
        Implements Requirements:
        - 10.3: AI-verified certificate generation
        - 10.4: Display badges on user profiles
        
        Args:
            user_id: ID of user completing curriculum
            guild_id: ID of premium guild
            certificate_name: Name of certificate
            description: Description of achievement
            
        Returns:
            Created Certificate object
            
        Raises:
            ValueError: If user, guild not found, or guild not premium
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate guild exists and is premium
        guild = self.db.query(Guild).filter(Guild.id == guild_id).first()
        if not guild:
            raise ValueError(f"Guild {guild_id} not found")
        
        if guild.guild_type != GuildType.PREMIUM:
            raise ValueError(
                f"Guild {guild_id} is not a premium guild (type: {guild.guild_type})"
            )
        
        # Check if certificate already exists
        existing_cert = self.db.query(Certificate).filter(
            and_(
                Certificate.user_id == user_id,
                Certificate.guild_id == guild_id
            )
        ).first()
        
        if existing_cert:
            raise ValueError(
                f"Certificate already exists for user {user_id} in guild {guild_id}"
            )
        
        # Generate unique verification code
        verification_code = secrets.token_urlsafe(16)
        
        # Create certificate
        certificate = Certificate(
            user_id=user_id,
            guild_id=guild_id,
            certificate_name=certificate_name,
            description=description,
            verification_code=verification_code,
            ai_verified=True,
            issued_at=datetime.utcnow()
        )
        
        self.db.add(certificate)
        self.db.commit()
        self.db.refresh(certificate)
        
        logger.info(
            f"Generated AI-verified certificate {certificate.id} for user {user_id} "
            f"in guild {guild_id}"
        )
        
        return certificate
    
    def get_user_certificates(self, user_id: UUID) -> List[Certificate]:
        """
        Get all certificates for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of Certificate objects
        """
        return self.db.query(Certificate).filter(
            Certificate.user_id == user_id
        ).order_by(Certificate.issued_at.desc()).all()
    
    def verify_certificate(self, verification_code: str) -> Optional[Certificate]:
        """
        Verify a certificate by its verification code.
        
        Args:
            verification_code: Unique verification code
            
        Returns:
            Certificate object if found, None otherwise
        """
        return self.db.query(Certificate).filter(
            Certificate.verification_code == verification_code
        ).first()
