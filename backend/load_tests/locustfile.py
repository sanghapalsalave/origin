"""
Load testing with Locust for ORIGIN Learning Platform.

Tests API performance under various load conditions.
"""
from locust import HttpUser, task, between
import random
import json

class OriginUser(HttpUser):
    """
    Simulates a user interacting with the ORIGIN platform.
    """
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when a user starts. Performs login."""
        # Register or login
        self.register_and_login()
    
    def register_and_login(self):
        """Register a new user and login."""
        # Generate random user
        user_id = random.randint(1000, 999999)
        self.email = f"loadtest{user_id}@example.com"
        self.password = "TestPassword123!"
        
        # Register
        response = self.client.post("/api/v1/auth/register", json={
            "email": self.email,
            "password": self.password,
            "full_name": f"Load Test User {user_id}"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.user_id = data.get("user_id")
        else:
            # Try login if registration failed
            response = self.client.post("/api/v1/auth/login", json={
                "email": self.email,
                "password": self.password
            })
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_id = data.get("user_id")
    
    @property
    def headers(self):
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.access_token}"
        } if hasattr(self, 'access_token') else {}
    
    @task(10)
    def health_check(self):
        """Test health check endpoint (most frequent)."""
        self.client.get("/health")
    
    @task(5)
    def get_profile(self):
        """Test getting user profile."""
        if hasattr(self, 'user_id'):
            self.client.get(
                f"/api/v1/users/{self.user_id}/profile",
                headers=self.headers
            )
    
    @task(3)
    def submit_portfolio(self):
        """Test portfolio submission."""
        if hasattr(self, 'user_id'):
            self.client.post(
                "/api/v1/onboarding/portfolio",
                headers=self.headers,
                json={
                    "github_url": "https://github.com/testuser",
                    "skills": ["Python", "JavaScript", "React"],
                    "experience_years": random.randint(1, 10)
                }
            )
    
    @task(2)
    def get_squad_matches(self):
        """Test squad matching."""
        if hasattr(self, 'user_id'):
            guild_id = "test-guild-id"
            self.client.get(
                f"/api/v1/matching/guilds/{guild_id}/matches",
                headers=self.headers
            )
    
    @task(2)
    def get_syllabus(self):
        """Test syllabus retrieval."""
        if hasattr(self, 'user_id'):
            squad_id = "test-squad-id"
            self.client.get(
                f"/api/v1/squads/{squad_id}/syllabus",
                headers=self.headers
            )
    
    @task(1)
    def send_chat_message(self):
        """Test chat message sending."""
        if hasattr(self, 'user_id'):
            channel_id = "test-channel-id"
            self.client.post(
                f"/api/v1/chat/{channel_id}/messages",
                headers=self.headers,
                json={
                    "content": f"Test message {random.randint(1, 1000)}",
                    "message_type": "text"
                }
            )


class PortfolioAnalysisUser(HttpUser):
    """
    Simulates users performing portfolio analysis (heavy operation).
    """
    wait_time = between(5, 15)
    
    def on_start(self):
        """Login."""
        self.email = f"portfolio{random.randint(1000, 9999)}@example.com"
        self.password = "TestPassword123!"
        
        response = self.client.post("/api/v1/auth/register", json={
            "email": self.email,
            "password": self.password,
            "full_name": "Portfolio Test User"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.user_id = data.get("user_id")
    
    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}"
        } if hasattr(self, 'access_token') else {}
    
    @task
    def analyze_portfolio(self):
        """Test portfolio analysis (should complete in < 5 seconds)."""
        if hasattr(self, 'user_id'):
            with self.client.post(
                "/api/v1/onboarding/portfolio",
                headers=self.headers,
                json={
                    "github_url": f"https://github.com/user{random.randint(1, 1000)}",
                    "linkedin_data": {
                        "experience": [
                            {
                                "title": "Software Engineer",
                                "company": "Tech Corp",
                                "years": 3
                            }
                        ]
                    },
                    "skills": ["Python", "JavaScript", "Docker"],
                    "experience_years": random.randint(1, 10)
                },
                catch_response=True
            ) as response:
                if response.elapsed.total_seconds() > 5:
                    response.failure(f"Portfolio analysis took {response.elapsed.total_seconds()}s (> 5s threshold)")


class SquadMatchingUser(HttpUser):
    """
    Simulates users performing squad matching (should complete in < 3 seconds).
    """
    wait_time = between(3, 10)
    
    def on_start(self):
        """Login."""
        self.email = f"matching{random.randint(1000, 9999)}@example.com"
        self.password = "TestPassword123!"
        
        response = self.client.post("/api/v1/auth/register", json={
            "email": self.email,
            "password": self.password,
            "full_name": "Matching Test User"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.user_id = data.get("user_id")
    
    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}"
        } if hasattr(self, 'access_token') else {}
    
    @task
    def find_squad_matches(self):
        """Test squad matching (should complete in < 3 seconds)."""
        if hasattr(self, 'user_id'):
            guild_id = f"guild-{random.randint(1, 10)}"
            with self.client.post(
                f"/api/v1/matching/guilds/{guild_id}/join",
                headers=self.headers,
                catch_response=True
            ) as response:
                if response.elapsed.total_seconds() > 3:
                    response.failure(f"Squad matching took {response.elapsed.total_seconds()}s (> 3s threshold)")
