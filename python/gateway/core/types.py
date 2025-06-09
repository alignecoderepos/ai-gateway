"""
Core type definitions for the AI Gateway.
"""
from typing import Dict, List, Optional, Union, Any, Literal, TypeVar, Generic
from enum import Enum
from pydantic import BaseModel, Field, model_validator
import uuid
from datetime import datetime


class Role(str, Enum):
    """Message roles in a chat conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class FinishReason(str, Enum):
    """Reasons why a generation might stop."""
    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    FUNCTION_CALL = "function_call"


class MessageContent(BaseModel):
    """Content part of a chat message."""
    type: str
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class ChatMessage(BaseModel):
    """A message in a chat conversation."""
    role: Role
    content: Union[str, List[MessageContent]]
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class ResponseFormat(BaseModel):
    """Format specification for model responses."""
    type: Literal["text", "json_object"] = "text"


class FunctionDef(BaseModel):
    """Definition of a function that can be called by the model."""
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any]


class ToolType(str, Enum):
    """Types of tools that can be used by models."""
    FUNCTION = "function"


class Tool(BaseModel):
    """Definition of a tool that can be used by the model."""
    type: ToolType
    function: FunctionDef


class ToolChoice(BaseModel):
    """Specification for which tool the model should use."""
    type: Optional[ToolType] = None
    function: Optional[Dict[str, Any]] = None


class StreamOptions(BaseModel):
    """Options for streaming responses."""
    include_usage: bool = False
    include_prompt: bool = False


class RequestUser(BaseModel):
    """Information about the user making the request."""
    id: str
    metadata: Optional[Dict[str, Any]] = None


class PromptCacheOptions(BaseModel):
    """Options for prompt caching."""
    enabled: bool = True
    ttl: Optional[int] = None  # Time-to-live in seconds


class ChatCompletionRequest(BaseModel):
    """Request for a chat completion."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    response_format: Optional[ResponseFormat] = None
    seed: Optional[int] = None
    functions: Optional[List[FunctionDef]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, ToolChoice]] = None
    stream_options: Optional[StreamOptions] = None
    
    class Config:
        extra = "allow"  # Allow extra fields for extensibility


class Usage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ToolCall(BaseModel):
    """Information about a tool call made by the model."""
    id: str
    type: ToolType
    function: Dict[str, Any]


class ChatCompletionResponseChoice(BaseModel):
    """A single completion choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[FinishReason] = None
    logprobs: Optional[Any] = None


class ChatCompletionStreamResponseChoice(BaseModel):
    """A single completion choice in a streaming chat completion response."""
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[FinishReason] = None
    logprobs: Optional[Any] = None


class ChatCompletionResponse(BaseModel):
    """Response from a chat completion request."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """Response chunk from a streaming chat completion request."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamResponseChoice]
    usage: Optional[Usage] = None
    system_fingerprint: Optional[str] = None


class EmbeddingRequest(BaseModel):
    """Request for embeddings."""
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None
    encoding_format: Optional[str] = None
    dimensions: Optional[int] = None


class EmbeddingData(BaseModel):
    """A single embedding result."""
    index: int
    embedding: List[float]
    object: str = "embedding"


class EmbeddingResponse(BaseModel):
    """Response from an embedding request."""
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: Usage


class ImageGenerationRequest(BaseModel):
    """Request for image generation."""
    model: str
    prompt: str
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    response_format: Optional[str] = "url"
    quality: Optional[str] = "standard"
    style: Optional[str] = "vivid"
    user: Optional[str] = None


class ImageData(BaseModel):
    """Data for a generated image."""
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """Response from an image generation request."""
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    data: List[ImageData]


class ModelListResponse(BaseModel):
    """Response for listing available models."""
    object: str = "list"
    data: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """Standardized error response."""
    error: Dict[str, Any]


# Guard-related types
class GuardEvaluation(BaseModel):
    """Result of a guardrail evaluation."""
    passed: bool
    score: Optional[float] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GuardResult(BaseModel):
    """Result from a guard evaluation."""
    id: str
    name: str
    evaluation: GuardEvaluation


T = TypeVar('T')


class GatewayResponse(BaseModel, Generic[T]):
    """Generic response wrapper for gateway operations."""
    response: T
    usage: Usage


class ProviderMetrics(BaseModel):
    """Metrics for a specific provider."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_latency_ms: int = 0
    avg_latency_ms: float = 0
    cost_usd: float = 0


# For type hinting
Headers = Dict[str, str]
JsonDict = Dict[str, Any]