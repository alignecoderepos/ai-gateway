"""
Tracing implementation for the AI Gateway.
"""
import logging
from typing import Optional, Dict, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from gateway.config.settings import settings
from gateway.constants import TELEMETRY_SERVICE_NAME, TELEMETRY_VERSION


logger = logging.getLogger(__name__)


def setup_tracing(service_name: Optional[str] = None) -> None:
    """
    Set up OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service (default: from settings)
    """
    # Skip if telemetry is not enabled
    if not settings.telemetry.enabled:
        logger.debug("Telemetry is disabled, skipping tracing setup")
        return
    
    # Skip if no OTLP endpoint is configured
    if not settings.telemetry.otlp_endpoint:
        logger.warning("No OTLP endpoint configured, skipping tracing setup")
        return
    
    try:
        # Set up tracer provider
        resource = Resource(attributes={
            SERVICE_NAME: service_name or settings.telemetry.service_name or TELEMETRY_SERVICE_NAME,
            "service.version": TELEMETRY_VERSION,
            "deployment.environment": settings.environment
        })
        
        tracer_provider = TracerProvider(resource=resource)
        
        # Set up exporter
        otlp_exporter = OTLPSpanExporter(endpoint=settings.telemetry.otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
        
        tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        logger.info(f"Tracing initialized with OTLP endpoint: {settings.telemetry.otlp_endpoint}")
        
    except Exception as e:
        logger.error(f"Error setting up tracing: {e}")


def get_tracer(name: str = "gateway") -> trace.Tracer:
    """
    Get a tracer instance.
    
    Args:
        name: Name of the tracer
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def create_span(name: str, attributes: Optional[Dict[str, Any]] = None, parent: Optional[trace.Span] = None) -> trace.Span:
    """
    Create a new span.
    
    Args:
        name: Name of the span
        attributes: Span attributes
        parent: Parent span
        
    Returns:
        New span
    """
    tracer = get_tracer()
    
    # Create context for the span
    if parent:
        context = trace.set_span_in_context(parent)
        return tracer.start_span(name, attributes=attributes, context=context)
    
    return tracer.start_span(name, attributes=attributes)