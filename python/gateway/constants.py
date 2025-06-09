"""
Constants used throughout the AI Gateway application.
"""

# Application info
APP_NAME = "AI Gateway"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "AI gateway for managing and routing LLM requests - Govern, Secure, and Optimize your AI Traffic"

# API Paths
API_PREFIX = "/v1"
HEALTH_PATH = "/health"
MODELS_PATH = "/models"
CHAT_COMPLETIONS_PATH = "/chat/completions"
COMPLETIONS_PATH = "/completions"
EMBEDDINGS_PATH = "/embeddings"
IMAGES_PATH = "/images/generations"

# Default models
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDINGS_MODEL = "text-embedding-3-small"
DEFAULT_IMAGE_MODEL = "dall-e-3"

# Headers
AUTH_HEADER = "Authorization"
CONTENT_TYPE_HEADER = "Content-Type"
USER_AGENT_HEADER = "User-Agent"
REQUEST_ID_HEADER = "X-Request-ID"
GATEWAY_VERSION_HEADER = "X-Gateway-Version"
GATEWAY_MODEL_HEADER = "X-Gateway-Model"
THREAD_ID_HEADER = "X-Thread-ID"
RUN_ID_HEADER = "X-Run-ID"

# Content types
JSON_CONTENT_TYPE = "application/json"
STREAM_CONTENT_TYPE = "text/event-stream"

# Timeouts (in seconds)
DEFAULT_REQUEST_TIMEOUT = 120.0
EMBEDDING_REQUEST_TIMEOUT = 60.0
IMAGE_REQUEST_TIMEOUT = 180.0

# Rate limiting
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_PERIOD = 60  # seconds

# Caching
DEFAULT_CACHE_TTL = 3600  # 1 hour in seconds

# Telemetry
TELEMETRY_SERVICE_NAME = "ai-gateway"
TELEMETRY_VERSION = APP_VERSION

# Provider names
PROVIDER_OPENAI = "openai"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_GEMINI = "gemini"
PROVIDER_BEDROCK = "bedrock"
PROVIDER_AZURE = "azure"
PROVIDER_MISTRAL = "mistral"

# Logo for CLI
LOGO = r"""
  ██       █████  ███    ██  ██████  ██████  ██████  
  ██      ██   ██ ████   ██ ██       ██   ██ ██   ██ 
  ██      ███████ ██ ██  ██ ██   ███ ██   ██ ██████  
  ██      ██   ██ ██  ██ ██ ██    ██ ██   ██ ██   ██ 
  ███████ ██   ██ ██   ████  ██████  ██████  ██████
"""