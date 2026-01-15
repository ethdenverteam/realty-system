"""
Centralized logging system - файлы + БД
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from functools import wraps
from flask import request, g, has_request_context
from app.database import db
from app.models.action_log import ActionLog
from app.config import Config


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to database"""
    
    def emit(self, record):
        """Write log record to database"""
        try:
            # Only log to DB if we have request context and it's an action
            if has_request_context() and hasattr(record, 'action'):
                # This will be handled by log_action function
                return
            
            # For errors, always log to DB if possible
            if record.levelno >= logging.ERROR:
                try:
                    log_entry = ActionLog(
                        user_id=getattr(g, 'current_user_id', None),
                        action=f"error_{record.levelname.lower()}",
                        details_json={
                            'message': record.getMessage(),
                            'module': record.module,
                            'funcName': record.funcName,
                            'lineno': record.lineno,
                            'pathname': record.pathname
                        },
                        ip_address=getattr(request, 'remote_addr', None) if has_request_context() else None,
                        user_agent=getattr(request, 'user_agent', {}).string if has_request_context() else None,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(log_entry)
                    db.session.commit()
                except Exception:
                    # Don't fail if DB logging fails
                    db.session.rollback()
        except Exception:
            pass  # Silently fail to avoid recursion


def setup_logging():
    """Setup centralized logging system"""
    # Create logs directory if it doesn't exist
    os.makedirs(Config.LOG_FOLDER, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-30s | %(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # File handler - all logs (rotating, 10MB, 10 files)
    all_logs_file = os.path.join(Config.LOG_FOLDER, 'app.log')
    file_handler = logging.handlers.RotatingFileHandler(
        all_logs_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Error handler - only errors (rotating, 5MB, 5 files)
    error_logs_file = os.path.join(Config.LOG_FOLDER, 'errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Database handler for errors
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(logging.ERROR)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(db_handler)
    
    # Set levels for third-party libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return root_logger


def log_action(action: str, user_id: int = None, details: dict = None, 
               ip_address: str = None, user_agent: str = None):
    """
    Log user action to database and file
    
    Args:
        action: Action name (e.g., 'user_login', 'object_created')
        user_id: User ID (optional, will try to get from request context)
        details: Additional details as dict
        ip_address: IP address (optional, will try to get from request)
        user_agent: User agent (optional, will try to get from request)
    """
    logger = logging.getLogger('app.actions')
    
    try:
        # Get from request context if available
        if has_request_context():
            if user_id is None and hasattr(g, 'current_user'):
                user_id = g.current_user.user_id if g.current_user else None
            if ip_address is None:
                ip_address = request.remote_addr
            if user_agent is None:
                user_agent = request.user_agent.string if request.user_agent else None
        
        # Create log entry
        log_entry = ActionLog(
            user_id=user_id,
            action=action,
            details_json=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        # Also log to file
        details_str = f" | Details: {details}" if details else ""
        logger.info(f"Action: {action} | UserID: {user_id}{details_str}")
        
    except Exception as e:
        # Don't fail if logging fails
        logger.error(f"Failed to log action {action}: {e}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass


def log_error(error: Exception, action: str = None, user_id: int = None, 
              details: dict = None):
    """
    Log error to database and file
    
    Args:
        error: Exception object
        action: Action that caused error
        user_id: User ID
        details: Additional details
    """
    logger = logging.getLogger('app.errors')
    
    try:
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'action': action,
        }
        if details:
            error_details.update(details)
        
        # Log to file
        logger.error(
            f"Error in {action or 'unknown'}: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
        
        # Log to database
        if has_request_context():
            log_action(
                action=action or 'error_occurred',
                user_id=user_id,
                details=error_details,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string if request.user_agent else None
            )
    except Exception:
        # Don't fail if error logging fails
        pass


def log_request():
    """Log HTTP request (called from middleware)"""
    if not has_request_context():
        return
    
    try:
        # Skip logging for static files, health checks, and metrics
        if (request.path.startswith('/static/') or 
            request.path == '/health' or 
            request.path == '/metrics'):
            return
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.user_id
        
        # Log request
        log_action(
            action=f"api_{request.method.lower()}_{request.endpoint or 'unknown'}",
            user_id=user_id,
            details={
                'path': request.path,
                'method': request.method,
                'endpoint': request.endpoint,
                'args': dict(request.args),
                'remote_addr': request.remote_addr,
            },
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
    except Exception:
        pass  # Don't fail request if logging fails


def log_response(response):
    """Log HTTP response (called from middleware)"""
    if not has_request_context():
        return response
    
    try:
        # Skip logging for static files, health checks, and metrics
        if (request.path.startswith('/static/') or 
            request.path == '/health' or 
            request.path == '/metrics'):
            return response
        
        # Get user ID if authenticated
        user_id = None
        if hasattr(g, 'current_user') and g.current_user:
            user_id = g.current_user.user_id
        
        # Log response
        logger = logging.getLogger('app.requests')
        logger.debug(
            f"{request.method} {request.path} | "
            f"Status: {response.status_code} | "
            f"UserID: {user_id or 'anonymous'}"
        )
    except Exception:
        pass
    
    return response

