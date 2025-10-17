"""
Core package initialization
"""
from app.core.config import settings
from app.core.logging_config import setup_logging

__all__ = ['settings', 'setup_logging']
