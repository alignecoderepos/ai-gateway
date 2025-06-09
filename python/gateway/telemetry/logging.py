"""
Logging configuration for the AI Gateway.
"""
import logging
import logging.config
import os
import sys
from typing import Optional, Dict, Any

from gateway.config.settings import settings


# Custom logger for request logging
request_logger = logging.getLogger("gateway.request")


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Log level (default: from settings)
    """
    # Use log level from arguments or settings or default to INFO
    log_level = log_level or settings.log_level or "INFO"
    
    # Convert string log level to constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Basic logging configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "json": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": numeric_level,
                "formatter": "standard",
                "stream": sys.stdout,
            },
            "request_handler": {
                "class": "logging.StreamHandler",
                "level": numeric_level,
                "formatter": "standard",
                "stream": sys.stdout,
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": True,
            },
            "gateway": {
                "handlers": ["console"],
                "level": numeric_level,
                "propagate": False,
            },
            "gateway.request": {
                "handlers": ["request_handler"],
                "level": numeric_level,
                "propagate": False,
            },
        },
    }
    
    # Use JSON formatter in production
    if settings.environment == "production":
        try:
            # Try to import the JSON formatter
            from pythonjsonlogger import jsonlogger
            logging_config["handlers"]["console"]["formatter"] = "json"
            logging_config["handlers"]["request_handler"]["formatter"] = "json"
        except ImportError:
            # Fall back to standard formatter if JSON formatter is not available
            logging.warning("pythonjsonlogger not installed, falling back to standard formatter")
    
    # Configure logging
    logging.config.dictConfig(logging_config)
    
    # Log configuration
    logging.info(f"Logging initialized with level: {log_level}")


class RequestLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter for request logging with additional context.
    """
    
    def process(self, msg, kwargs):
        """
        Process the log message and add extra context.
        
        Args:
            msg: Log message
            kwargs: Logging kwargs
            
        Returns:
            Processed message and kwargs
        """
        # Add request ID and other context to the log message
        request_id = kwargs.get("extra", {}).get("request_id", "unknown")
        return f"[{request_id}] {msg}", kwargs