"""
Error tracking configuration for Sentry or similar services.

Provides centralized error tracking and alerting.
"""
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Flag to track if Sentry is initialized
_sentry_initialized = False


def init_error_tracking() -> None:
    """
    Initialize error tracking service (Sentry).
    
    Only initializes if SENTRY_DSN is configured in settings.
    """
    global _sentry_initialized
    
    if _sentry_initialized:
        return
    
    # Check if Sentry DSN is configured
    sentry_dsn = getattr(settings, 'SENTRY_DSN', None)
    
    if not sentry_dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.ENVIRONMENT,
            release=settings.VERSION,
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% for profiling
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                CeleryIntegration(),
            ],
            # Set custom tags
            before_send=before_send_handler,
        )
        
        _sentry_initialized = True
        logger.info("Sentry error tracking initialized")
        
    except ImportError:
        logger.warning("Sentry SDK not installed, error tracking disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {str(e)}")


def before_send_handler(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process events before sending to Sentry.
    
    Can be used to filter out certain errors or add custom context.
    
    Args:
        event: Sentry event data
        hint: Additional context
        
    Returns:
        Modified event or None to drop the event
    """
    # Add custom tags
    if 'tags' not in event:
        event['tags'] = {}
    
    event['tags']['service'] = 'origin-backend'
    
    # Filter out certain errors (e.g., health check failures)
    if 'request' in event and event['request'].get('url', '').endswith('/health'):
        return None
    
    return event


def capture_exception(
    error: Exception,
    context: Dict[str, Any] = None,
    level: str = 'error'
) -> None:
    """
    Capture an exception and send to error tracking service.
    
    Args:
        error: Exception to capture
        context: Additional context data
        level: Error level (error, warning, info)
    """
    if not _sentry_initialized:
        logger.error(f"Exception occurred: {str(error)}", exc_info=error)
        return
    
    try:
        import sentry_sdk
        
        # Add context if provided
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                scope.level = level
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)
            
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {str(e)}")


def capture_message(
    message: str,
    level: str = 'info',
    context: Dict[str, Any] = None
) -> None:
    """
    Capture a message and send to error tracking service.
    
    Args:
        message: Message to capture
        level: Message level (error, warning, info)
        context: Additional context data
    """
    if not _sentry_initialized:
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message)
        return
    
    try:
        import sentry_sdk
        
        # Add context if provided
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                scope.level = level
                sentry_sdk.capture_message(message)
        else:
            sentry_sdk.capture_message(message, level=level)
            
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {str(e)}")


def set_user_context(user_id: str, email: str = None, username: str = None) -> None:
    """
    Set user context for error tracking.
    
    Args:
        user_id: User ID
        email: User email (optional)
        username: Username (optional)
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        
        sentry_sdk.set_user({
            'id': user_id,
            'email': email,
            'username': username,
        })
        
    except Exception as e:
        logger.error(f"Failed to set user context in Sentry: {str(e)}")


def clear_user_context() -> None:
    """Clear user context from error tracking."""
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.set_user(None)
        
    except Exception as e:
        logger.error(f"Failed to clear user context in Sentry: {str(e)}")


def add_breadcrumb(
    message: str,
    category: str = 'default',
    level: str = 'info',
    data: Dict[str, Any] = None
) -> None:
    """
    Add a breadcrumb for error tracking.
    
    Breadcrumbs provide context about what happened before an error.
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Breadcrumb level
        data: Additional data
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
        
    except Exception as e:
        logger.error(f"Failed to add breadcrumb in Sentry: {str(e)}")
