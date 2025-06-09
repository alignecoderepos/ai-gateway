"""
Router implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, Union
import logging
import random

from gateway.core.types import ChatCompletionRequest
from gateway.core.models import model_registry
from gateway.config.models import Router, RouterStrategy
from gateway.errors.exceptions import RouterError, ModelNotFoundError


logger = logging.getLogger(__name__)

# Type alias for target
Target = Dict[str, Any]


class RoutingEngine:
    """
    Routing engine for directing requests to appropriate models and providers.
    Implements various routing strategies including fallback, percentage-based,
    random, and optimized routing.
    """
    
    def __init__(self, routers: Optional[List[Router]] = None):
        """
        Initialize the routing engine.
        
        Args:
            routers: List of router configurations
        """
        self.routers = routers or []
        self._router_map: Dict[str, Router] = {}
        
        # Build router map for quick lookup
        for router in self.routers:
            self._router_map[router.name] = router
    
    def add_router(self, router: Router) -> None:
        """
        Add a router to the engine.
        
        Args:
            router: Router configuration to add
        """
        self.routers.append(router)
        self._router_map[router.name] = router
    
    def get_router(self, name: str) -> Optional[Router]:
        """
        Get a router by name.
        
        Args:
            name: Name of the router to retrieve
            
        Returns:
            Router configuration if found, None otherwise
        """
        return self._router_map.get(name)
    
    async def route_chat_request(
        self, 
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Route a chat completion request to an appropriate target.
        
        Args:
            request: Chat completion request to route
            context: Additional context for routing decision
            
        Returns:
            Target configuration (model and provider)
            
        Raises:
            RouterError: If routing fails
            ModelNotFoundError: If the requested model is not found
        """
        model_name = request.model
        
        # Check if the model is a router
        if model_name.startswith("router/"):
            router_name = model_name.split("/", 1)[1]
            router = self.get_router(router_name)
            
            if not router:
                raise RouterError(f"Router not found: {router_name}")
            
            return await self._apply_routing_strategy(router, request, context)
        
        # If not a router, look up the model directly
        model = model_registry.get_model(model_name)
        if not model:
            raise ModelNotFoundError(f"Model not found: {model_name}")
        
        # Return direct model target
        return {
            "model": model.inference_provider.model_name,
            "provider": model.inference_provider.provider
        }
    
    async def _apply_routing_strategy(
        self,
        router: Router,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Apply a routing strategy to select a target.
        
        Args:
            router: Router configuration
            request: Chat completion request
            context: Additional context
            
        Returns:
            Selected target
            
        Raises:
            RouterError: If strategy application fails
        """
        if not router.targets:
            raise RouterError(f"Router {router.name} has no targets")
        
        strategy_type = router.strategy.type
        
        try:
            if strategy_type == "fallback":
                return await self._apply_fallback_strategy(router, request, context)
            elif strategy_type == "percentage":
                return await self._apply_percentage_strategy(router, request, context)
            elif strategy_type == "random":
                return await self._apply_random_strategy(router, request, context)
            elif strategy_type == "optimized":
                return await self._apply_optimized_strategy(router, request, context)
            else:
                raise RouterError(f"Unknown routing strategy: {strategy_type}")
        except Exception as e:
            logger.error(f"Error applying routing strategy {strategy_type}: {e}")
            raise RouterError(f"Routing strategy error: {e}")
    
    async def _apply_fallback_strategy(
        self,
        router: Router,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Apply fallback strategy - try targets in order until one succeeds.
        For the initial selection, we just return the first target.
        Actual fallback happens during execution.
        
        Args:
            router: Router configuration
            request: Chat completion request
            context: Additional context
            
        Returns:
            First target in the list
        """
        if not router.targets:
            raise RouterError(f"Router {router.name} has no targets")
        
        return router.targets[0]
    
    async def _apply_percentage_strategy(
        self,
        router: Router,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Apply percentage-based strategy (A/B testing).
        
        Args:
            router: Router configuration
            request: Chat completion request
            context: Additional context
            
        Returns:
            Selected target based on percentage distribution
        """
        if not router.targets:
            raise RouterError(f"Router {router.name} has no targets")
        
        if not hasattr(router.strategy, "targets_percentages"):
            raise RouterError("Percentage strategy requires targets_percentages")
        
        percentages = router.strategy.targets_percentages
        
        if len(percentages) != len(router.targets):
            raise RouterError(
                f"Number of percentages ({len(percentages)}) does not match "
                f"number of targets ({len(router.targets)})"
            )
        
        # Normalize percentages if they don't sum to 100
        total = sum(percentages)
        if total != 100:
            percentages = [p * 100 / total for p in percentages]
        
        # Select target based on random value and cumulative percentages
        rand_val = random.uniform(0, 100)
        cumulative = 0
        
        for i, pct in enumerate(percentages):
            cumulative += pct
            if rand_val <= cumulative:
                return router.targets[i]
        
        # Fallback to last target if something goes wrong
        return router.targets[-1]
    
    async def _apply_random_strategy(
        self,
        router: Router,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Apply random strategy - select a target randomly.
        
        Args:
            router: Router configuration
            request: Chat completion request
            context: Additional context
            
        Returns:
            Randomly selected target
        """
        if not router.targets:
            raise RouterError(f"Router {router.name} has no targets")
        
        return random.choice(router.targets)
    
    async def _apply_optimized_strategy(
        self,
        router: Router,
        request: ChatCompletionRequest,
        context: Optional[Any] = None
    ) -> Target:
        """
        Apply optimized strategy - select target based on metrics.
        
        Args:
            router: Router configuration
            request: Chat completion request
            context: Additional context
            
        Returns:
            Selected target based on optimization metric
            
        Note:
            This is a simplified implementation. A full implementation would
            require a metrics collection system and more sophisticated logic.
        """
        if not router.targets:
            raise RouterError(f"Router {router.name} has no targets")
        
        if not hasattr(router.strategy, "metric"):
            raise RouterError("Optimized strategy requires a metric selector")
        
        # For now, without a full metrics system, we fall back to random selection
        # In a real implementation, we would use the metric to choose the best target
        logger.warning("Optimized routing strategy not fully implemented, falling back to random")
        return random.choice(router.targets)