"""
Token counting utilities for the AI Gateway.
"""
import tiktoken
import logging
from typing import List, Union, Dict, Any, Optional

from gateway.core.types import ChatMessage


logger = logging.getLogger(__name__)


# Cache for tiktoken encoders
_encoder_cache: Dict[str, Any] = {}


def get_encoder(model_name: str) -> Any:
    """
    Get the appropriate encoder for a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Tiktoken encoder
    """
    # Check cache first
    if model_name in _encoder_cache:
        return _encoder_cache[model_name]
    
    # Determine encoding based on model name
    encoding_name = "cl100k_base"  # Default for newer models
    
    # GPT-4 and ChatGPT models
    if "gpt-4" in model_name or "gpt-3.5" in model_name:
        encoding_name = "cl100k_base"
    # GPT-3 models
    elif "text-davinci" in model_name or "text-curie" in model_name:
        encoding_name = "p50k_base"
    # Ada and Babbage models
    elif "text-ada" in model_name or "text-babbage" in model_name:
        encoding_name = "r50k_base"
    # Anthropic models
    elif "claude" in model_name:
        encoding_name = "cl100k_base"
    # Gemini models
    elif "gemini" in model_name:
        encoding_name = "cl100k_base"
    # Mistral models
    elif "mistral" in model_name:
        encoding_name = "cl100k_base"
    # Llama models
    elif "llama" in model_name:
        encoding_name = "cl100k_base"
    
    try:
        encoder = tiktoken.get_encoding(encoding_name)
        _encoder_cache[model_name] = encoder
        return encoder
    except Exception as e:
        logger.warning(f"Error getting encoder for model {model_name}: {e}")
        # Fall back to cl100k_base
        encoder = tiktoken.get_encoding("cl100k_base")
        _encoder_cache[model_name] = encoder
        return encoder


def count_tokens(text: str, model_name: str) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: Text to count tokens for
        model_name: Name of the model
        
    Returns:
        Number of tokens
    """
    encoder = get_encoder(model_name)
    return len(encoder.encode(text))


def count_message_tokens(message: ChatMessage, model_name: str) -> int:
    """
    Count the number of tokens in a chat message.
    
    Args:
        message: Chat message
        model_name: Name of the model
        
    Returns:
        Number of tokens
    """
    # Get the encoder
    encoder = get_encoder(model_name)
    
    # Start with tokens for message role (usually 1-2 tokens)
    num_tokens = 4  # Base tokens for each message
    
    # Add tokens for role
    num_tokens += len(encoder.encode(message.role.value))
    
    # Handle different content types
    if isinstance(message.content, str):
        # Simple text content
        num_tokens += len(encoder.encode(message.content))
    elif isinstance(message.content, list):
        # Structured content (text + images)
        for part in message.content:
            if hasattr(part, "type") and part.type == "text" and part.text:
                num_tokens += len(encoder.encode(part.text))
            elif hasattr(part, "type") and part.type == "image_url":
                # Images have a higher token cost (approximately)
                # This is a rough estimate based on common image encodings
                num_tokens += 85  # Base cost for small images
    
    # Add tokens for name if present
    if message.name:
        num_tokens += len(encoder.encode(message.name)) + 1
    
    # Add tokens for tool_calls if present
    if message.tool_calls:
        for tool_call in message.tool_calls:
            # Add tokens for id and type
            num_tokens += len(encoder.encode(tool_call.get("id", ""))) + 1
            num_tokens += len(encoder.encode(tool_call.get("type", ""))) + 1
            
            # Add tokens for function details
            if "function" in tool_call:
                function = tool_call["function"]
                num_tokens += len(encoder.encode(function.get("name", ""))) + 1
                
                # Arguments are typically JSON
                arguments = function.get("arguments", "{}")
                if isinstance(arguments, str):
                    num_tokens += len(encoder.encode(arguments))
                else:
                    # If it's already a dict or other object, convert to string
                    import json
                    num_tokens += len(encoder.encode(json.dumps(arguments)))
    
    # Add tokens for function_call if present (legacy)
    if message.function_call:
        # Add tokens for name
        num_tokens += len(encoder.encode(message.function_call.get("name", ""))) + 1
        
        # Add tokens for arguments
        arguments = message.function_call.get("arguments", "{}")
        if isinstance(arguments, str):
            num_tokens += len(encoder.encode(arguments))
        else:
            # If it's already a dict or other object, convert to string
            import json
            num_tokens += len(encoder.encode(json.dumps(arguments)))
    
    # Add tokens for tool_call_id if present
    if message.tool_call_id:
        num_tokens += len(encoder.encode(message.tool_call_id)) + 1
    
    return num_tokens


def count_messages_tokens(messages: List[ChatMessage], model_name: str) -> int:
    """
    Count the number of tokens in a list of chat messages.
    
    Args:
        messages: List of chat messages
        model_name: Name of the model
        
    Returns:
        Number of tokens
    """
    num_tokens = 0
    
    # Add tokens for each message
    for message in messages:
        num_tokens += count_message_tokens(message, model_name)
    
    # Add tokens for chat overhead (varies by model)
    if "gpt-4" in model_name or "gpt-3.5" in model_name:
        # OpenAI models have a small overhead
        num_tokens += 3
    elif "claude" in model_name:
        # Anthropic models have a different overhead
        num_tokens += 7
    else:
        # Default overhead
        num_tokens += 3
    
    return num_tokens


def count_request_tokens(messages: List[ChatMessage], model_name: str, max_tokens: Optional[int] = None) -> Dict[str, int]:
    """
    Count the total number of tokens in a chat completion request.
    
    Args:
        messages: List of chat messages
        model_name: Name of the model
        max_tokens: Maximum number of tokens for completion (if specified)
        
    Returns:
        Dictionary with token counts (prompt, completion, total)
    """
    # Count prompt tokens
    prompt_tokens = count_messages_tokens(messages, model_name)
    
    # Use max_tokens for completion tokens if specified
    completion_tokens = max_tokens or 0
    
    # Calculate total tokens
    total_tokens = prompt_tokens + completion_tokens
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens
    }