"""
Cost calculation for the AI Gateway.
"""
import logging
from typing import Dict, Optional

from gateway.core.models import model_registry, ModelDefinition


logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Cost calculator for API usage.
    """
    
    def __init__(self):
        """Initialize the cost calculator."""
        pass
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate the cost for API usage.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        # Get model definition
        model_def = model_registry.get_model(model)
        
        if not model_def:
            # If model not found, use default pricing
            logger.warning(f"Model '{model}' not found, using default pricing")
            return self._calculate_default_cost(model, input_tokens, output_tokens)
        
        # Calculate cost based on model pricing
        return self._calculate_model_cost(model_def, input_tokens, output_tokens)
    
    def _calculate_model_cost(self, model_def: ModelDefinition, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost based on model pricing.
        
        Args:
            model_def: Model definition
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        # Get pricing information
        input_price = model_def.price.per_input_token
        output_price = model_def.price.per_output_token
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        
        return input_cost + output_cost
    
    def _calculate_default_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost using default pricing.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        # Default pricing (per million tokens)
        default_pricing = {
            # OpenAI
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-4-vision": {"input": 30.0, "output": 60.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4o": {"input": 5.0, "output": 15.0},
            "gpt-4o-mini": {"input": 2.0, "output": 6.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
            "text-embedding-3-small": {"input": 0.2, "output": 0.0},
            "text-embedding-3-large": {"input": 1.0, "output": 0.0},
            "dall-e-3": {"input": 0.0, "output": 0.0},  # Special pricing
            
            # Anthropic
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            
            # Google
            "gemini-pro": {"input": 0.5, "output": 1.5},
            "gemini-pro-vision": {"input": 0.5, "output": 1.5},
            "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
            
            # Mistral
            "mistral-small": {"input": 1.0, "output": 3.0},
            "mistral-medium": {"input": 2.7, "output": 8.1},
            "mistral-large": {"input": 8.0, "output": 24.0},
        }
        
        # Find matching pricing
        pricing = None
        for model_prefix, price in default_pricing.items():
            if model.startswith(model_prefix):
                pricing = price
                break
        
        # Use default pricing if no match found
        if pricing is None:
            pricing = {"input": 1.0, "output": 3.0}
            logger.warning(f"No pricing found for model '{model}', using default pricing")
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost


# Global cost calculator instance
cost_calculator = CostCalculator()