"""
Logging configuration
"""
import os
import logging
import logging.handlers
from app.core.config import settings


def setup_logging():
    """Setup application logging"""
    
    # Create logs directory
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler with rotation
            logging.handlers.RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('tensorflow').setLevel(logging.ERROR)
    logging.getLogger('torch').setLevel(logging.WARNING)
