"""
Telemetry setup for the AI Gateway.
"""
import logging
from typing import Optional

from gateway.telemetry.logging import setup_logging
from gateway.telemetry.tracing import setup_tracing
from gateway.config.settings import settings


logger = logging.getLogger(__name__)


def init_telemetry(log_level: Optional[str] = None) -> None:
    """
    Initialize all telemetry components.
    
    Args:
        log_level: Log level (default: from settings)
    """
    # Set up logging first
    setup_logging(log_level)
    
    # Set up tracing
    if settings.telemetry.enabled:
        setup_tracing()
        logger.info("Telemetry initialized")
    else:
        logger.info("Telemetry is disabled")