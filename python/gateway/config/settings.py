from typing import List, Optional, Dict, Any, Union
import os
from pathlib import Path

from pydantic import Field, field_validator, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class HttpSettings(BaseSettings):
    host: str = Field("0.0.0.0", description="Host address to bind the server to")
    port: int = Field(8000, description="Port to bind the server to")
    workers: int = Field(1, description="Number of worker processes")
    cors_allow_origins: List[str] = Field(
        ["*"], description="List of origins that are allowed to make cross-origin requests"
    )
    cors_allow_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"], 
        description="List of HTTP methods that are allowed for CORS"
    )
    cors_allow_headers: List[str] = Field(
        ["Authorization", "Content-Type"], 
        description="List of HTTP headers that are allowed for CORS"
    )
    cors_allow_credentials: bool = Field(
        False, 
        description="Whether to allow credentials (cookies, authorization headers) in CORS requests"
    )
    
    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string of origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @field_validator("cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def validate_comma_separated_list(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string into a list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class TelemetrySettings(BaseSettings):
    enabled: bool = Field(False, description="Whether to enable telemetry collection")
    otlp_endpoint: Optional[str] = Field(None, description="OpenTelemetry collector endpoint")
    service_name: str = Field("ai-gateway", description="Service name for telemetry")


class CostControlSettings(BaseSettings):
    enabled: bool = Field(False, description="Whether to enable cost control features")
    monthly_budget: Optional[float] = Field(None, description="Monthly budget limit in USD")
    default_token_limit: int = Field(
        16000, description="Default maximum tokens (input + output) per request"
    )
    warning_threshold: float = Field(
        0.8, description="Threshold (as a proportion of budget) at which to issue warnings"
    )


class CacheSettings(BaseSettings):
    enabled: bool = Field(False, description="Whether to enable caching")
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    default_ttl: int = Field(3600, description="Default time-to-live for cache entries in seconds")


class Settings(BaseSettings):
    """Main application settings class that combines all sub-settings."""
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    # Basic settings
    environment: str = Field("development", description="Application environment")
    log_level: str = Field("INFO", description="Logging level")
    config_path: Optional[str] = Field(None, description="Path to YAML configuration file")
    
    # Component settings
    http: HttpSettings = Field(default_factory=HttpSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    cost_control: CostControlSettings = Field(default_factory=CostControlSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    
    # Provider API keys
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    gemini_api_key: Optional[str] = Field(None, description="Google Gemini API key")
    
    # AWS Bedrock
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS secret access key")
    aws_region: Optional[str] = Field(None, description="AWS region")
    
    # Azure OpenAI
    azure_openai_api_key: Optional[str] = Field(None, description="Azure OpenAI API key")
    azure_openai_endpoint: Optional[str] = Field(None, description="Azure OpenAI endpoint")
    
    # Rate limiting
    enable_rate_limit: bool = Field(False, description="Whether to enable rate limiting")
    rate_limit_requests: int = Field(100, description="Number of requests allowed per period")
    rate_limit_period: int = Field(60, description="Rate limit period in seconds")

    @classmethod
    def load(cls) -> "Settings":
        """Load settings from environment variables and optional config file."""
        settings = cls()
        
        # If config file path is provided, merge with settings from file
        if settings.config_path:
            try:
                import yaml
                config_path = Path(settings.config_path)
                if config_path.exists():
                    with open(config_path, "r") as f:
                        file_config = yaml.safe_load(f)
                    # Update settings with values from file
                    # Implementation depends on how you want to handle merging
                    # This is a simplistic approach
                    if file_config:
                        for k, v in file_config.items():
                            if hasattr(settings, k):
                                setattr(settings, k, v)
            except Exception as e:
                # Log error but continue with environment variables
                print(f"Error loading config file: {e}")
                
        return settings


# Create a global settings instance
settings = Settings.load()