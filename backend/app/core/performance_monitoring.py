"""
Performance monitoring utilities.

Tracks API response times, database query performance, and external service latency.
"""
import time
import logging
from typing import Callable, Any, Dict
from functools import wraps
from contextlib import contextmanager
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Performance thresholds (in seconds)
THRESHOLDS = {
    'api_response': 0.5,  # p95 < 500ms
    'portfolio_analysis': 5.0,  # < 5 seconds
    'squad_matching': 3.0,  # < 3 seconds
    'syllabus_generation': 10.0,  # < 10 seconds
    'chat_message_delivery': 2.0,  # < 2 seconds
    'database_query': 0.1,  # < 100ms
    'external_api': 2.0,  # < 2 seconds
}


@contextmanager
def track_performance(operation: str, threshold: float = None):
    """
    Context manager to track operation performance.
    
    Args:
        operation: Name of the operation being tracked
        threshold: Optional custom threshold (uses default if not provided)
        
    Example:
        with track_performance('portfolio_analysis'):
            analyze_portfolio()
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        # Get threshold
        if threshold is None:
            threshold = THRESHOLDS.get(operation, 1.0)
        
        # Log performance
        log_data = {
            'operation': operation,
            'duration_seconds': round(duration, 3),
            'threshold_seconds': threshold,
            'exceeded_threshold': duration > threshold
        }
        
        if duration > threshold:
            logger.warning(
                f"Performance threshold exceeded for {operation}",
                extra={'extra_fields': log_data}
            )
        else:
            logger.info(
                f"Performance tracked for {operation}",
                extra={'extra_fields': log_data}
            )


def monitor_performance(operation: str = None, threshold: float = None):
    """
    Decorator to monitor function performance.
    
    Args:
        operation: Name of the operation (uses function name if not provided)
        threshold: Optional custom threshold
        
    Example:
        @monitor_performance('portfolio_analysis', 5.0)
        def analyze_portfolio():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation or func.__name__
            
            with track_performance(op_name, threshold):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


async def monitor_async_performance(operation: str = None, threshold: float = None):
    """
    Decorator to monitor async function performance.
    
    Args:
        operation: Name of the operation (uses function name if not provided)
        threshold: Optional custom threshold
        
    Example:
        @monitor_async_performance('api_endpoint', 0.5)
        async def get_user():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            op_name = operation or func.__name__
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                # Get threshold
                thresh = threshold if threshold is not None else THRESHOLDS.get(op_name, 1.0)
                
                # Log performance
                log_data = {
                    'operation': op_name,
                    'duration_seconds': round(duration, 3),
                    'threshold_seconds': thresh,
                    'exceeded_threshold': duration > thresh
                }
                
                if duration > thresh:
                    logger.warning(
                        f"Performance threshold exceeded for {op_name}",
                        extra={'extra_fields': log_data}
                    )
                else:
                    logger.info(
                        f"Performance tracked for {op_name}",
                        extra={'extra_fields': log_data}
                    )
        
        return wrapper
    return decorator


class PerformanceMetrics:
    """
    Class to collect and aggregate performance metrics.
    """
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record(self, operation: str, duration: float) -> None:
        """
        Record a performance metric.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """
        Get statistics for an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Dictionary with min, max, avg, p95, p99
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = sorted(self.metrics[operation])
        count = len(durations)
        
        return {
            'count': count,
            'min': durations[0],
            'max': durations[-1],
            'avg': sum(durations) / count,
            'p50': durations[int(count * 0.5)],
            'p95': durations[int(count * 0.95)],
            'p99': durations[int(count * 0.99)],
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to their statistics
        """
        return {
            operation: self.get_stats(operation)
            for operation in self.metrics.keys()
        }
    
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()


# Global metrics instance
metrics = PerformanceMetrics()


def record_metric(operation: str, duration: float) -> None:
    """
    Record a performance metric.
    
    Args:
        operation: Operation name
        duration: Duration in seconds
    """
    metrics.record(operation, duration)


def get_metrics_summary() -> Dict[str, Dict[str, float]]:
    """
    Get summary of all performance metrics.
    
    Returns:
        Dictionary with statistics for all operations
    """
    return metrics.get_all_stats()
