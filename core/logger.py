"""
Core Logging Module

Provides structured logging configuration with JSON formatting for production.
"""
import logging
import json
from datetime import datetime
from core.config import settings


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production environments.
    
    Formats log records as JSON for easy parsing by log aggregation systems.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request_id if present (for future request tracing)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging():
    """
    Configure logging based on environment settings.
    
    - Development: Standard formatter with DEBUG level
    - Production: JSON formatter with INFO level
    """
    # Determine log level based on environment
    if settings.ENV == "development":
        level = logging.DEBUG
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        level = logging.INFO
        formatter = JSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add stream handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
