"""
Usage limits for the AI Gateway.
"""
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta

from gateway.errors.exceptions import QuotaExceededError
from gateway.usage.storage import UsageStorage


logger = logging.getLogger(__name__)


class UsageLimit:
    """
    Usage limit definition.
    """
    
    def __init__(
        self,
        limit_type: str,
        value: float,
        period: Optional[str] = None,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a usage limit.
        
        Args:
            limit_type: Type of limit (tokens, cost, requests)
            value: Limit value
            period: Time period (hourly, daily, monthly, total)
            user_id: User ID (if limit is user-specific)
            model: Model name (if limit is model-specific)
            provider: Provider name (if limit is provider-specific)
            metadata: Additional metadata
        """
        self.limit_type = limit_type
        self.value = value
        self.period = period
        self.user_id = user_id
        self.model = model
        self.provider = provider
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the limit to a dictionary.
        
        Returns:
            Dictionary representation of the limit
        """
        return {
            "limit_type": self.limit_type,
            "value": self.value,
            "period": self.period,
            "user_id": self.user_id,
            "model": self.model,
            "provider": self.provider,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageLimit":
        """
        Create a limit from a dictionary.
        
        Args:
            data: Dictionary representation of the limit
            
        Returns:
            Usage limit
        """
        return cls(
            limit_type=data["limit_type"],
            value=data["value"],
            period=data.get("period"),
            user_id=data.get("user_id"),
            model=data.get("model"),
            provider=data.get("provider"),
            metadata=data.get("metadata", {})
        )


class UsageLimitChecker:
    """
    Usage limit checker.
    """
    
    def __init__(self, storage: UsageStorage):
        """
        Initialize the limit checker.
        
        Args:
            storage: Usage storage
        """
        self.storage = storage
        self.limits: List[UsageLimit] = []
    
    def add_limit(self, limit: UsageLimit) -> None:
        """
        Add a usage limit.
        
        Args:
            limit: Usage limit
        """
        self.limits.append(limit)
        logger.debug(f"Added usage limit: {limit.to_dict()}")
    
    def remove_limit(self, limit: UsageLimit) -> None:
        """
        Remove a usage limit.
        
        Args:
            limit: Usage limit
        """
        self.limits.remove(limit)
        logger.debug(f"Removed usage limit: {limit.to_dict()}")
    
    def clear_limits(self) -> None:
        """Clear all usage limits."""
        self.limits = []
        logger.debug("Cleared all usage limits")
    
    async def check_limits(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        tokens: Optional[int] = None,
        cost: Optional[float] = None
    ) -> None:
        """
        Check if usage limits are exceeded.
        
        Args:
            user_id: User ID
            model: Model name
            provider: Provider name
            tokens: Number of tokens for the current request
            cost: Cost for the current request
            
        Raises:
            QuotaExceededError: If any limit is exceeded
        """
        # Skip if no limits are defined
        if not self.limits:
            return
        
        # Get applicable limits
        applicable_limits = []
        for limit in self.limits:
            # Check if limit applies to user
            if limit.user_id and limit.user_id != user_id:
                continue
            
            # Check if limit applies to model
            if limit.model and limit.model != model:
                continue
            
            # Check if limit applies to provider
            if limit.provider and limit.provider != provider:
                continue
            
            # Include limit
            applicable_limits.append(limit)
        
        # Skip if no applicable limits
        if not applicable_limits:
            return
        
        # Check each applicable limit
        for limit in applicable_limits:
            # Get time range based on period
            start_time, end_time = self._get_time_range(limit.period)
            
            # Get usage summary
            summary = await self.storage.get_usage_summary(
                start_time=start_time,
                end_time=end_time,
                user_id=limit.user_id,
                model=limit.model,
                provider=limit.provider
            )
            
            # Check limit based on type
            if limit.limit_type == "tokens":
                current_usage = summary["total_tokens"]
                projected_usage = current_usage + (tokens or 0)
                
                if projected_usage > limit.value:
                    logger.warning(
                        f"Token limit exceeded: {projected_usage} > {limit.value}",
                        extra={
                            "user_id": user_id,
                            "model": model,
                            "provider": provider,
                            "current_usage": current_usage,
                            "projected_usage": projected_usage,
                            "limit": limit.value,
                            "period": limit.period
                        }
                    )
                    
                    raise QuotaExceededError(
                        f"Token limit exceeded: {projected_usage} > {limit.value} for period {limit.period or 'total'}"
                    )
                
            elif limit.limit_type == "cost":
                current_usage = summary["total_cost"]
                projected_usage = current_usage + (cost or 0)
                
                if projected_usage > limit.value:
                    logger.warning(
                        f"Cost limit exceeded: ${projected_usage:.6f} > ${limit.value:.6f}",
                        extra={
                            "user_id": user_id,
                            "model": model,
                            "provider": provider,
                            "current_usage": current_usage,
                            "projected_usage": projected_usage,
                            "limit": limit.value,
                            "period": limit.period
                        }
                    )
                    
                    raise QuotaExceededError(
                        f"Cost limit exceeded: ${projected_usage:.6f} > ${limit.value:.6f} for period {limit.period or 'total'}"
                    )
                
            elif limit.limit_type == "requests":
                current_usage = summary["total_requests"]
                projected_usage = current_usage + 1
                
                if projected_usage > limit.value:
                    logger.warning(
                        f"Request limit exceeded: {projected_usage} > {limit.value}",
                        extra={
                            "user_id": user_id,
                            "model": model,
                            "provider": provider,
                            "current_usage": current_usage,
                            "projected_usage": projected_usage,
                            "limit": limit.value,
                            "period": limit.period
                        }
                    )
                    
                    raise QuotaExceededError(
                        f"Request limit exceeded: {projected_usage} > {limit.value} for period {limit.period or 'total'}"
                    )
    
    def _get_time_range(self, period: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Get time range based on period.
        
        Args:
            period: Time period (hourly, daily, monthly, total)
            
        Returns:
            Tuple of (start_time, end_time)
        """
        now = datetime.now()
        
        if period == "hourly":
            start_time = now.replace(minute=0, second=0, microsecond=0)
            end_time = now
        elif period == "daily":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == "monthly":
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == "yearly":
            start_time = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        else:
            # No period means all time
            start_time = None
            end_time = None
        
        return start_time, end_time