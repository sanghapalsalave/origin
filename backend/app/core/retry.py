"""
Retry Decorator with Exponential Backoff

Provides a reusable decorator for retrying external API calls with exponential backoff.

Implements Requirement 13.12: API rate limit handling with exponential backoff

Design Specifications:
- Initial delay: 1 second
- Multiplier: 2x
- Maximum delay: 32 seconds
- Maximum attempts: 5
- Jitter: ±25% random variation
"""
import time
import logging
import functools
from typing import Callable, Type, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
):
    """
    Decorator that retries a function with exponential backoff on failure.
    
    Implements Requirement 13.12: API retry with exponential backoff
    
    The backoff strategy follows:
    - delay = base_delay * (2 ** retry_count) * jitter
    - jitter = random value between 0.75 and 1.25 (±25% variation)
    - delay is capped at max_delay
    
    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 32.0)
        exceptions: Tuple of exception types to catch and retry (default: (Exception,))
        on_retry: Optional callback function called on each retry with (exception, retry_count, delay)
        
    Returns:
        Decorated function that retries on failure
        
    Example:
        @retry_with_exponential_backoff(max_retries=3, exceptions=(requests.RequestException,))
        def fetch_data(url):
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    
                    # If we've exhausted all retries, raise the exception
                    if retry_count > max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} retries: {str(e)}"
                        )
                        raise
                    
                    # Calculate exponential backoff with jitter
                    # Jitter: random value between 0.75 and 1.25 (±25%)
                    jitter = 0.75 + 0.5 * (time.time() % 1)
                    delay = base_delay * (2 ** (retry_count - 1)) * jitter
                    delay = min(delay, max_delay)
                    
                    # Log the retry attempt
                    logger.warning(
                        f"{func.__name__} failed (attempt {retry_count}/{max_retries}), "
                        f"retrying in {delay:.2f} seconds: {str(e)}"
                    )
                    
                    # Call the optional callback
                    if on_retry:
                        on_retry(e, retry_count, delay)
                    
                    # Wait before retrying
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise RuntimeError(f"{func.__name__} failed after {max_retries} retries")
        
        return wrapper
    return decorator


def retry_on_rate_limit(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    rate_limit_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Specialized retry decorator for rate-limited APIs.
    
    This is a convenience wrapper around retry_with_exponential_backoff
    specifically designed for handling API rate limits.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 5)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 32.0)
        rate_limit_exceptions: Tuple of rate limit exception types to catch
        
    Returns:
        Decorated function that retries on rate limit errors
        
    Example:
        from github import RateLimitExceededException
        
        @retry_on_rate_limit(rate_limit_exceptions=(RateLimitExceededException,))
        def fetch_github_user(username):
            return github_client.get_user(username)
    """
    def on_retry_callback(exception: Exception, retry_count: int, delay: float):
        logger.info(f"Rate limit hit, backing off for {delay:.2f} seconds")
    
    return retry_with_exponential_backoff(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exceptions=rate_limit_exceptions,
        on_retry=on_retry_callback
    )


class RetryConfig:
    """
    Configuration class for retry behavior.
    
    Provides default retry configurations for different types of external services.
    """
    
    # Default configuration (follows design spec)
    DEFAULT_MAX_RETRIES = 5
    DEFAULT_BASE_DELAY = 1.0
    DEFAULT_MAX_DELAY = 32.0
    
    # GitHub API configuration
    GITHUB_MAX_RETRIES = 5
    GITHUB_BASE_DELAY = 1.0
    GITHUB_MAX_DELAY = 32.0
    
    # LinkedIn API configuration
    LINKEDIN_MAX_RETRIES = 5
    LINKEDIN_BASE_DELAY = 1.0
    LINKEDIN_MAX_DELAY = 32.0
    
    # Web scraping configuration (more lenient)
    WEB_SCRAPING_MAX_RETRIES = 3
    WEB_SCRAPING_BASE_DELAY = 1.0
    WEB_SCRAPING_MAX_DELAY = 16.0
    
    # OpenAI/LLM API configuration
    LLM_MAX_RETRIES = 3
    LLM_BASE_DELAY = 2.0
    LLM_MAX_DELAY = 60.0
    
    # Pinecone/Vector DB configuration
    VECTOR_DB_MAX_RETRIES = 3
    VECTOR_DB_BASE_DELAY = 1.0
    VECTOR_DB_MAX_DELAY = 16.0
