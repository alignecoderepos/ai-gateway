"""
Usage storage for the AI Gateway.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class UsageRecord:
    """
    Record of API usage.
    """
    
    def __init__(
        self,
        timestamp: datetime,
        provider: str,
        model: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        cost: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a usage record.
        
        Args:
            timestamp: Time of the usage
            provider: Provider name
            model: Model name
            user_id: User ID
            request_id: Request ID
            thread_id: Thread ID for conversation context
            run_id: Run ID for tracking executions
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total number of tokens
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
            error: Error message if the request failed
            cost: Cost of the request in USD
            metadata: Additional metadata
        """
        self.timestamp = timestamp
        self.provider = provider
        self.model = model
        self.user_id = user_id
        self.request_id = request_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.latency_ms = latency_ms
        self.success = success
        self.error = error
        self.cost = cost
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the record to a dictionary.
        
        Returns:
            Dictionary representation of the record
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "thread_id": self.thread_id,
            "run_id": self.run_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "cost": self.cost,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UsageRecord":
        """
        Create a record from a dictionary.
        
        Args:
            data: Dictionary representation of the record
            
        Returns:
            Usage record
        """
        # Convert timestamp string to datetime
        timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            timestamp=timestamp,
            provider=data["provider"],
            model=data["model"],
            user_id=data.get("user_id"),
            request_id=data.get("request_id"),
            thread_id=data.get("thread_id"),
            run_id=data.get("run_id"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            latency_ms=data.get("latency_ms", 0),
            success=data.get("success", True),
            error=data.get("error"),
            cost=data.get("cost", 0.0),
            metadata=data.get("metadata", {})
        )


class UsageStorage(ABC):
    """
    Abstract base class for usage storage.
    """
    
    @abstractmethod
    async def record_usage(
        self,
        provider: str,
        model: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record API usage.
        
        Args:
            provider: Provider name
            model: Model name
            user_id: User ID
            request_id: Request ID
            thread_id: Thread ID for conversation context
            run_id: Run ID for tracking executions
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total number of tokens
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
            error: Error message if the request failed
            cost: Cost of the request in USD
            metadata: Additional metadata
        """
        pass
    
    @abstractmethod
    async def get_usage(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> List[UsageRecord]:
        """
        Get usage records.
        
        Args:
            start_time: Start time
            end_time: End time
            provider: Provider name
            model: Model name
            user_id: User ID
            thread_id: Thread ID
            run_id: Run ID
            
        Returns:
            List of usage records
        """
        pass
    
    @abstractmethod
    async def get_usage_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary.
        
        Args:
            start_time: Start time
            end_time: End time
            provider: Provider name
            model: Model name
            user_id: User ID
            thread_id: Thread ID
            run_id: Run ID
            group_by: Fields to group by
            
        Returns:
            Usage summary
        """
        pass


class InMemoryUsageStorage(UsageStorage):
    """
    In-memory implementation of usage storage.
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.records: List[UsageRecord] = []
    
    async def record_usage(
        self,
        provider: str,
        model: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: int = 0,
        success: bool = True,
        error: Optional[str] = None,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record API usage.
        
        Args:
            provider: Provider name
            model: Model name
            user_id: User ID
            request_id: Request ID
            thread_id: Thread ID for conversation context
            run_id: Run ID for tracking executions
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total number of tokens
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
            error: Error message if the request failed
            cost: Cost of the request in USD
            metadata: Additional metadata
        """
        # Calculate cost if not provided
        if cost is None:
            # In a real implementation, this would use a cost calculator
            # For now, we use a simple approximation
            input_cost = input_tokens * 0.0000005  # $0.0005 per 1000 tokens
            output_cost = output_tokens * 0.0000015  # $0.0015 per 1000 tokens
            cost = input_cost + output_cost
        
        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            user_id=user_id,
            request_id=request_id,
            thread_id=thread_id,
            run_id=run_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error,
            cost=cost,
            metadata=metadata
        )
        
        # Store record
        self.records.append(record)
        
        # Log usage
        logger.debug(
            f"Recorded usage: {provider}/{model}, {total_tokens} tokens, ${cost:.6f}",
            extra={
                "user_id": user_id,
                "request_id": request_id,
                "thread_id": thread_id,
                "run_id": run_id,
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost": cost,
                "success": success
            }
        )
    
    async def get_usage(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None
    ) -> List[UsageRecord]:
        """
        Get usage records.
        
        Args:
            start_time: Start time
            end_time: End time
            provider: Provider name
            model: Model name
            user_id: User ID
            thread_id: Thread ID
            run_id: Run ID
            
        Returns:
            List of usage records
        """
        # Set default times if not provided
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=30)  # Last 30 days
        
        # Filter records
        filtered_records = []
        for record in self.records:
            # Check time range
            if record.timestamp < start_time or record.timestamp > end_time:
                continue
            
            # Check provider
            if provider and record.provider != provider:
                continue
            
            # Check model
            if model and record.model != model:
                continue
            
            # Check user ID
            if user_id and record.user_id != user_id:
                continue
            
            # Check thread ID
            if thread_id and record.thread_id != thread_id:
                continue
            
            # Check run ID
            if run_id and record.run_id != run_id:
                continue
            
            # Include record
            filtered_records.append(record)
        
        return filtered_records
    
    async def get_usage_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary.
        
        Args:
            start_time: Start time
            end_time: End time
            provider: Provider name
            model: Model name
            user_id: User ID
            thread_id: Thread ID
            run_id: Run ID
            group_by: Fields to group by
            
        Returns:
            Usage summary
        """
        # Get filtered records
        records = await self.get_usage(
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            model=model,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Initialize summary
        summary = {
            "total_requests": len(records),
            "successful_requests": sum(1 for r in records if r.success),
            "failed_requests": sum(1 for r in records if not r.success),
            "total_tokens": sum(r.total_tokens for r in records),
            "input_tokens": sum(r.input_tokens for r in records),
            "output_tokens": sum(r.output_tokens for r in records),
            "total_cost": sum(r.cost for r in records),
            "avg_latency_ms": sum(r.latency_ms for r in records) / len(records) if records else 0
        }
        
        # Group by specified fields
        if group_by:
            groups = {}
            
            for record in records:
                # Create group key
                group_key = []
                for field in group_by:
                    if hasattr(record, field):
                        group_key.append(str(getattr(record, field)))
                    else:
                        group_key.append("unknown")
                
                group_key_str = "|".join(group_key)
                
                # Initialize group if not exists
                if group_key_str not in groups:
                    groups[group_key_str] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "total_tokens": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_cost": 0,
                        "total_latency_ms": 0
                    }
                    
                    # Add group fields
                    for i, field in enumerate(group_by):
                        if field == "timestamp":
                            # Special handling for timestamp
                            groups[group_key_str][field] = record.timestamp.isoformat()
                        else:
                            groups[group_key_str][field] = getattr(record, field, None)
                
                # Update group stats
                group = groups[group_key_str]
                group["total_requests"] += 1
                if record.success:
                    group["successful_requests"] += 1
                else:
                    group["failed_requests"] += 1
                group["total_tokens"] += record.total_tokens
                group["input_tokens"] += record.input_tokens
                group["output_tokens"] += record.output_tokens
                group["total_cost"] += record.cost
                group["total_latency_ms"] += record.latency_ms
            
            # Calculate averages and add to summary
            for group_key, group in groups.items():
                if group["total_requests"] > 0:
                    group["avg_latency_ms"] = group["total_latency_ms"] / group["total_requests"]
                del group["total_latency_ms"]
            
            summary["groups"] = groups
        
        return summary