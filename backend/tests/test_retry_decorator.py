"""
Tests for retry decorator with exponential backoff.

Tests the retry decorator functionality including:
- Successful retry after failures
- Exponential backoff timing
- Maximum retry limit
- Exception handling
- Jitter application

Validates Requirement 13.12: API retry with exponential backoff
"""
import time
import pytest
from unittest.mock import Mock, patch
from app.core.retry import (
    retry_with_exponential_backoff,
    retry_on_rate_limit,
    RetryConfig
)


class TestRetryDecorator:
    """Test retry decorator with exponential backoff."""
    
    def test_success_on_first_try(self):
        """Test that function succeeds on first try without retry."""
        mock_func = Mock(return_value="success")
        
        @retry_with_exponential_backoff(max_retries=3)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_success_after_retries(self):
        """Test that function succeeds after some failures."""
        mock_func = Mock(side_effect=[
            Exception("Fail 1"),
            Exception("Fail 2"),
            "success"
        ])
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def test_func():
            return mock_func()
        
        with pytest.raises(Exception, match="Always fails"):
            test_func()
        
        # Should try initial + 3 retries = 4 total
        assert mock_func.call_count == 4
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delay correctly."""
        call_times = []
        
        def failing_func():
            call_times.append(time.time())
            if len(call_times) < 4:
                raise Exception("Retry me")
            return "success"
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.1, max_delay=1.0)
        def test_func():
            return failing_func()
        
        result = test_func()
        
        assert result == "success"
        assert len(call_times) == 4
        
        # Check that delays increase (with some tolerance for jitter)
        # First retry: ~0.1s, Second retry: ~0.2s, Third retry: ~0.4s
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        delay3 = call_times[3] - call_times[2]
        
        # Delays should generally increase (accounting for jitter)
        assert delay1 < delay2 * 1.5  # Allow for jitter
        assert delay2 < delay3 * 1.5
    
    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        call_times = []
        
        def failing_func():
            call_times.append(time.time())
            if len(call_times) < 6:
                raise Exception("Retry me")
            return "success"
        
        @retry_with_exponential_backoff(max_retries=5, base_delay=1.0, max_delay=0.5)
        def test_func():
            return failing_func()
        
        result = test_func()
        
        assert result == "success"
        
        # Check that no delay exceeds max_delay (with tolerance)
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 0.7  # max_delay + some tolerance for jitter
    
    def test_specific_exception_types(self):
        """Test that only specified exceptions are retried."""
        
        class RetryableError(Exception):
            pass
        
        class NonRetryableError(Exception):
            pass
        
        mock_func = Mock(side_effect=NonRetryableError("Don't retry"))
        
        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            exceptions=(RetryableError,)
        )
        def test_func():
            return mock_func()
        
        # Should raise immediately without retry
        with pytest.raises(NonRetryableError):
            test_func()
        
        assert mock_func.call_count == 1
    
    def test_on_retry_callback(self):
        """Test that on_retry callback is called on each retry."""
        callback_calls = []
        
        def on_retry_callback(exception, retry_count, delay):
            callback_calls.append({
                "exception": str(exception),
                "retry_count": retry_count,
                "delay": delay
            })
        
        mock_func = Mock(side_effect=[
            Exception("Fail 1"),
            Exception("Fail 2"),
            "success"
        ])
        
        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.01,
            on_retry=on_retry_callback
        )
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert len(callback_calls) == 2  # Two retries before success
        assert callback_calls[0]["retry_count"] == 1
        assert callback_calls[1]["retry_count"] == 2
    
    def test_retry_config_constants(self):
        """Test that RetryConfig has correct default values."""
        assert RetryConfig.DEFAULT_MAX_RETRIES == 5
        assert RetryConfig.DEFAULT_BASE_DELAY == 1.0
        assert RetryConfig.DEFAULT_MAX_DELAY == 32.0
        
        assert RetryConfig.GITHUB_MAX_RETRIES == 5
        assert RetryConfig.GITHUB_BASE_DELAY == 1.0
        assert RetryConfig.GITHUB_MAX_DELAY == 32.0
        
        assert RetryConfig.WEB_SCRAPING_MAX_RETRIES == 3
        assert RetryConfig.WEB_SCRAPING_MAX_DELAY == 16.0
    
    def test_retry_on_rate_limit_decorator(self):
        """Test the specialized rate limit retry decorator."""
        
        class RateLimitError(Exception):
            pass
        
        mock_func = Mock(side_effect=[
            RateLimitError("Rate limited"),
            "success"
        ])
        
        @retry_on_rate_limit(
            max_retries=3,
            base_delay=0.01,
            rate_limit_exceptions=(RateLimitError,)
        )
        def test_func():
            return mock_func()
        
        result = test_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_jitter_variation(self):
        """Test that jitter adds variation to delays."""
        delays = []
        
        for _ in range(10):
            call_times = []
            
            def failing_func():
                call_times.append(time.time())
                if len(call_times) < 2:
                    raise Exception("Retry me")
                return "success"
            
            @retry_with_exponential_backoff(max_retries=1, base_delay=0.1)
            def test_func():
                return failing_func()
            
            test_func()
            
            if len(call_times) >= 2:
                delay = call_times[1] - call_times[0]
                delays.append(delay)
        
        # Check that delays vary (not all the same)
        # With jitter, delays should be between 0.075 and 0.125 (±25%)
        assert len(set([round(d, 3) for d in delays])) > 1  # At least some variation
        assert all(0.05 < d < 0.15 for d in delays)  # Within expected range
    
    def test_zero_retries(self):
        """Test behavior with max_retries=0."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_with_exponential_backoff(max_retries=0, base_delay=0.01)
        def test_func():
            return mock_func()
        
        with pytest.raises(Exception, match="Fail"):
            test_func()
        
        # Should only try once (no retries)
        assert mock_func.call_count == 1
    
    def test_function_with_arguments(self):
        """Test that decorated function preserves arguments."""
        mock_func = Mock(return_value="success")
        
        @retry_with_exponential_backoff(max_retries=3)
        def test_func(arg1, arg2, kwarg1=None):
            return mock_func(arg1, arg2, kwarg1=kwarg1)
        
        result = test_func("a", "b", kwarg1="c")
        
        assert result == "success"
        mock_func.assert_called_once_with("a", "b", kwarg1="c")
    
    def test_function_metadata_preserved(self):
        """Test that functools.wraps preserves function metadata."""
        
        @retry_with_exponential_backoff(max_retries=3)
        def test_func():
            """Test function docstring."""
            return "success"
        
        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."


class TestRetryIntegration:
    """Integration tests for retry decorator with real scenarios."""
    
    def test_simulated_api_rate_limit(self):
        """Simulate API rate limit scenario."""
        
        class APIRateLimitError(Exception):
            pass
        
        # Simulate API that fails 3 times then succeeds
        api_calls = []
        
        def api_call():
            api_calls.append(time.time())
            if len(api_calls) <= 3:
                raise APIRateLimitError("Rate limit exceeded")
            return {"data": "success"}
        
        @retry_with_exponential_backoff(
            max_retries=5,
            base_delay=0.05,
            exceptions=(APIRateLimitError,)
        )
        def fetch_data():
            return api_call()
        
        result = fetch_data()
        
        assert result == {"data": "success"}
        assert len(api_calls) == 4  # 3 failures + 1 success
    
    def test_simulated_network_timeout(self):
        """Simulate network timeout scenario."""
        import requests
        
        # Simulate network that times out twice then succeeds
        attempt_count = [0]
        
        def network_call():
            attempt_count[0] += 1
            if attempt_count[0] <= 2:
                raise requests.exceptions.Timeout("Connection timeout")
            return "success"
        
        @retry_with_exponential_backoff(
            max_retries=3,
            base_delay=0.05,
            exceptions=(requests.exceptions.Timeout,)
        )
        def fetch_url():
            return network_call()
        
        result = fetch_url()
        
        assert result == "success"
        assert attempt_count[0] == 3
    
    def test_mixed_exception_types(self):
        """Test handling of mixed exception types."""
        
        class RetryableError(Exception):
            pass
        
        class FatalError(Exception):
            pass
        
        # Simulate API that has retryable errors then a fatal error
        call_count = [0]
        
        def api_call():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RetryableError("Temporary issue")
            elif call_count[0] == 2:
                raise FatalError("Fatal error")
            return "success"
        
        @retry_with_exponential_backoff(
            max_retries=5,
            base_delay=0.01,
            exceptions=(RetryableError,)
        )
        def fetch_data():
            return api_call()
        
        # Should retry once, then hit fatal error and stop
        with pytest.raises(FatalError):
            fetch_data()
        
        assert call_count[0] == 2
