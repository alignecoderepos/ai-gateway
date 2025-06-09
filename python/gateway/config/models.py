from typing import Dict, List, Optional, Union, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class ModelCapability(str, Enum):
    """Capabilities that a model might support."""
    TOOLS = "tools"
    VISION = "vision"
    STREAMING = "streaming"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"


class ModelIOFormat(str, Enum):
    """Input/output formats supported by models."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


class ModelType(str, Enum):
    """Types of models available in the system."""
    COMPLETIONS = "completions"
    EMBEDDINGS = "embeddings"
    IMAGE_GENERATION = "image_generation"


class ModelLimits(BaseModel):
    """Limitations for a specific model."""
    max_context_size: int = Field(..., description="Maximum context size in tokens")
    max_output_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    max_input_tokens: Optional[int] = Field(None, description="Maximum input tokens")
    max_requests_per_minute: Optional[int] = Field(None, description="Rate limit for this model")


class ModelPrice(BaseModel):
    """Pricing information for a model."""
    per_input_token: float = Field(..., description="Cost per input token in USD (scaled by 1M)")
    per_output_token: float = Field(..., description="Cost per output token in USD (scaled by 1M)")
    valid_from: Optional[str] = Field(None, description="Date from which this pricing is valid")


class InferenceProviderConfig(BaseModel):
    """Configuration for a specific inference provider."""
    provider: str = Field(..., description="Provider name (e.g., openai, anthropic)")
    model_name: str = Field(..., description="Model name at the provider")
    endpoint: Optional[str] = Field(None, description="Custom endpoint URL")
    api_key: Optional[str] = Field(None, description="API key override")
    api_version: Optional[str] = Field(None, description="API version")
    extra_headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")


class ModelParameter(BaseModel):
    """Definition of a model parameter."""
    type: str = Field(..., description="Parameter type (float, int, string, boolean, etc.)")
    default: Optional[Any] = Field(None, description="Default value")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(False, description="Whether the parameter is required")
    min: Optional[float] = Field(None, description="Minimum value (for numeric parameters)")
    max: Optional[float] = Field(None, description="Maximum value (for numeric parameters)")
    step: Optional[float] = Field(None, description="Step size (for numeric parameters)")


class ModelDefinition(BaseModel):
    """Definition of a model available in the system."""
    model: str = Field(..., description="Model identifier in the gateway")
    model_provider: str = Field(..., description="Original provider of the model")
    inference_provider: InferenceProviderConfig = Field(..., description="Inference provider config")
    price: ModelPrice = Field(..., description="Pricing information")
    input_formats: List[ModelIOFormat] = Field(..., description="Supported input formats")
    output_formats: List[ModelIOFormat] = Field(..., description="Supported output formats")
    capabilities: List[ModelCapability] = Field(default_factory=list, description="Model capabilities")
    type: ModelType = Field(..., description="Model type")
    limits: ModelLimits = Field(..., description="Model limits")
    description: str = Field("", description="Model description")
    parameters: Optional[Dict[str, ModelParameter]] = Field(None, description="Available parameters")


class RouterStrategy(BaseModel):
    """Base class for routing strategies."""
    type: str = Field(..., description="Strategy type")


class FallbackStrategy(RouterStrategy):
    """Simple fallback strategy that tries models in order."""
    type: Literal["fallback"] = "fallback"


class PercentageStrategy(RouterStrategy):
    """Percentage-based (A/B testing) strategy."""
    type: Literal["percentage"] = "percentage"
    targets_percentages: List[float] = Field(..., description="Percentage distribution across targets")


class RandomStrategy(RouterStrategy):
    """Random selection strategy."""
    type: Literal["random"] = "random"


class MetricSelector(BaseModel):
    """Metric selection for optimized routing."""
    name: str = Field(..., description="Metric name")
    order: Literal["asc", "desc"] = Field("asc", description="Sort order (asc or desc)")


class OptimizedStrategy(RouterStrategy):
    """Optimized strategy that selects based on metrics."""
    type: Literal["optimized"] = "optimized"
    metric: MetricSelector = Field(..., description="Metric to optimize for")


class MetricsDuration(str, Enum):
    """Time window for metrics collection."""
    TOTAL = "total"
    LAST_15_MINUTES = "last_15_minutes"
    LAST_HOUR = "last_hour"


class Router(BaseModel):
    """Definition of a router that can route requests to different models."""
    name: str = Field(..., description="Router name")
    strategy: Union[FallbackStrategy, PercentageStrategy, RandomStrategy, OptimizedStrategy] = Field(
        ..., description="Routing strategy"
    )
    targets: List[Dict[str, Any]] = Field(default_factory=list, description="Target models/providers")
    metrics_duration: Optional[MetricsDuration] = Field(None, description="Time window for metrics")


class CorsOptions(BaseModel):
    """CORS configuration options."""
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    allow_methods: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )
    allow_headers: List[str] = Field(default_factory=lambda: ["Authorization", "Content-Type"])
    allow_credentials: bool = False
    max_age: int = 600  # 10 minutes


class HttpConfig(BaseModel):
    """HTTP server configuration."""
    host: str = Field("0.0.0.0", description="Host to bind to")
    port: int = Field(8000, description="Port to listen on")
    workers: int = Field(1, description="Number of worker processes")
    cors: CorsOptions = Field(default_factory=CorsOptions, description="CORS configuration")


class GuardrailsConfig(BaseModel):
    """Configuration for content safety guardrails."""
    enabled: bool = Field(False, description="Whether guardrails are enabled")
    default_guards: List[str] = Field(default_factory=list, description="Default guardrails to apply")
    guardrails_path: Optional[str] = Field(None, description="Path to guardrails definitions")


class GatewayConfig(BaseModel):
    """Main configuration for the AI Gateway."""
    http: HttpConfig = Field(default_factory=HttpConfig, description="HTTP server configuration")
    guardrails: GuardrailsConfig = Field(
        default_factory=GuardrailsConfig, description="Guardrails configuration"
    )
    models: List[ModelDefinition] = Field(default_factory=list, description="Available models")
    routers: List[Router] = Field(default_factory=list, description="Routing configurations")

    @model_validator(mode="after")
    def validate_routers_targets(self) -> "GatewayConfig":
        """Validate that router targets reference valid models."""
        model_ids = {model.model for model in self.models}
        
        for router in self.routers:
            for target in router.targets:
                if "model" in target and target["model"] not in model_ids:
                    # This is just a warning, not an error, as the model might be added later
                    print(f"Warning: Router '{router.name}' references unknown model '{target['model']}'")
        
        return self


def load_config(file_path: str) -> GatewayConfig:
    """Load configuration from a YAML file."""
    import yaml
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(path, "r") as f:
        config_data = yaml.safe_load(f)
    
    return GatewayConfig.model_validate(config_data)