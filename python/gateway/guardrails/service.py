"""
Guardrails service for the AI Gateway.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

from gateway.core.types import ChatCompletionRequest, ChatCompletionResponse, ChatMessage
from gateway.config.settings import settings
from gateway.errors.exceptions import GuardrailError


logger = logging.getLogger(__name__)


class GuardrailEvaluator(ABC):
    """
    Abstract base class for guardrail evaluators.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the evaluator name."""
        pass
    
    @abstractmethod
    async def evaluate_input(self, request: ChatCompletionRequest, context: Optional[Any] = None) -> bool:
        """
        Evaluate input against guardrails.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Returns:
            True if input passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        pass
    
    @abstractmethod
    async def evaluate_output(self, response: ChatCompletionResponse, context: Optional[Any] = None) -> bool:
        """
        Evaluate output against guardrails.
        
        Args:
            response: Chat completion response
            context: Additional context
            
        Returns:
            True if output passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        pass


class RegexGuardrail(GuardrailEvaluator):
    """
    Regex-based guardrail evaluator.
    """
    
    def __init__(self, name: str, patterns: List[str], mode: str = "block", description: str = ""):
        """
        Initialize the regex guardrail.
        
        Args:
            name: Guardrail name
            patterns: List of regex patterns
            mode: Evaluation mode (block, allow)
            description: Guardrail description
        """
        self._name = name
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        self.mode = mode
        self.description = description
    
    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return self._name
    
    async def evaluate_input(self, request: ChatCompletionRequest, context: Optional[Any] = None) -> bool:
        """
        Evaluate input against guardrails.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Returns:
            True if input passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Get last user message
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            return True
        
        last_message = user_messages[-1]
        
        # Get content text
        content = last_message.content
        if isinstance(content, list):
            # Handle structured content
            text_parts = []
            for part in content:
                if hasattr(part, "type") and part.type == "text" and part.text:
                    text_parts.append(part.text)
            
            content = " ".join(text_parts)
        
        # Skip if content is not a string
        if not isinstance(content, str):
            return True
        
        # Check patterns
        for pattern in self.patterns:
            match = pattern.search(content)
            if match:
                # In block mode, a match means violation
                if self.mode == "block":
                    raise GuardrailError(
                        f"Input violates guardrail '{self.name}': {self.description or 'Blocked content'}"
                    )
                # In allow mode, a match means compliance
                else:
                    return True
        
        # In block mode, no match means compliance
        if self.mode == "block":
            return True
        # In allow mode, no match means violation
        else:
            raise GuardrailError(
                f"Input violates guardrail '{self.name}': {self.description or 'Required content missing'}"
            )
    
    async def evaluate_output(self, response: ChatCompletionResponse, context: Optional[Any] = None) -> bool:
        """
        Evaluate output against guardrails.
        
        Args:
            response: Chat completion response
            context: Additional context
            
        Returns:
            True if output passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Get first choice
        if not response.choices:
            return True
        
        first_choice = response.choices[0]
        message = first_choice.message
        
        # Get content text
        content = message.content
        if isinstance(content, list):
            # Handle structured content
            text_parts = []
            for part in content:
                if hasattr(part, "type") and part.type == "text" and part.text:
                    text_parts.append(part.text)
            
            content = " ".join(text_parts)
        
        # Skip if content is not a string
        if not isinstance(content, str):
            return True
        
        # Check patterns
        for pattern in self.patterns:
            match = pattern.search(content)
            if match:
                # In block mode, a match means violation
                if self.mode == "block":
                    raise GuardrailError(
                        f"Output violates guardrail '{self.name}': {self.description or 'Blocked content'}"
                    )
                # In allow mode, a match means compliance
                else:
                    return True
        
        # In block mode, no match means compliance
        if self.mode == "block":
            return True
        # In allow mode, no match means violation
        else:
            raise GuardrailError(
                f"Output violates guardrail '{self.name}': {self.description or 'Required content missing'}"
            )


class SchemaGuardrail(GuardrailEvaluator):
    """
    Schema-based guardrail evaluator.
    """
    
    def __init__(self, name: str, schema: Dict[str, Any], description: str = ""):
        """
        Initialize the schema guardrail.
        
        Args:
            name: Guardrail name
            schema: JSON schema
            description: Guardrail description
        """
        self._name = name
        self.schema = schema
        self.description = description
        
        # Import jsonschema here to avoid dependency issues
        try:
            import jsonschema
            self.validator = jsonschema.Draft7Validator(schema)
        except ImportError:
            logger.warning("jsonschema not installed, schema validation will not work")
            self.validator = None
    
    @property
    def name(self) -> str:
        """Get the evaluator name."""
        return self._name
    
    async def evaluate_input(self, request: ChatCompletionRequest, context: Optional[Any] = None) -> bool:
        """
        Evaluate input against guardrails.
        
        Args:
            request: Chat completion request
            context: Additional context
            
        Returns:
            True if input passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Skip schema validation for input (usually applied to output)
        return True
    
    async def evaluate_output(self, response: ChatCompletionResponse, context: Optional[Any] = None) -> bool:
        """
        Evaluate output against guardrails.
        
        Args:
            response: Chat completion response
            context: Additional context
            
        Returns:
            True if output passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Skip if validator is not available
        if not self.validator:
            logger.warning("Schema validation skipped: jsonschema not installed")
            return True
        
        # Get first choice
        if not response.choices:
            return True
        
        first_choice = response.choices[0]
        message = first_choice.message
        
        # Get content text
        content = message.content
        if isinstance(content, list):
            # Handle structured content
            text_parts = []
            for part in content:
                if hasattr(part, "type") and part.type == "text" and part.text:
                    text_parts.append(part.text)
            
            content = " ".join(text_parts)
        
        # Skip if content is not a string
        if not isinstance(content, str):
            return True
        
        # Try to parse content as JSON
        try:
            import json
            data = json.loads(content)
        except json.JSONDecodeError:
            # If output format is explicitly JSON, this is a violation
            if hasattr(response, "response_format") and response.response_format == "json_object":
                raise GuardrailError(
                    f"Output violates guardrail '{self.name}': Invalid JSON format"
                )
            # Otherwise, skip schema validation for non-JSON content
            return True
        
        # Validate against schema
        try:
            errors = list(self.validator.iter_errors(data))
            if errors:
                error_messages = [f"{e.path}: {e.message}" for e in errors]
                raise GuardrailError(
                    f"Output violates guardrail '{self.name}': Schema validation failed\n"
                    f"{', '.join(error_messages)}"
                )
        except Exception as e:
            if not isinstance(e, GuardrailError):
                logger.error(f"Schema validation error: {e}")
                raise GuardrailError(
                    f"Output violates guardrail '{self.name}': {str(e)}"
                )
            raise
        
        return True


class GuardrailsService:
    """
    Service for managing and applying guardrails.
    """
    
    def __init__(self):
        """Initialize the guardrails service."""
        self.evaluators: Dict[str, GuardrailEvaluator] = {}
        self.enabled = settings.guardrails.enabled
        
        # Initialize default guardrails
        self._init_default_guardrails()
    
    def _init_default_guardrails(self) -> None:
        """Initialize default guardrails."""
        # Skip if guardrails are disabled
        if not self.enabled:
            return
        
        # Add profanity filter
        self.add_evaluator(
            RegexGuardrail(
                name="profanity",
                patterns=[
                    r"\b(f[u*]ck|sh[i*]t|b[i*]tch|a[s*]{2}hole|c[u*]nt)\b",
                    r"\b(n[i*]gg[e*]r|f[a*]gg[o*]t|r[e*]t[a*]rd)\b"
                ],
                mode="block",
                description="Blocks content with profanity"
            )
        )
        
        # Add PII filter
        self.add_evaluator(
            RegexGuardrail(
                name="pii",
                patterns=[
                    r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # SSN
                    r"\b\d{16}\b",  # Credit card
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"  # Email
                ],
                mode="block",
                description="Blocks content with personally identifiable information"
            )
        )
        
        # Add default guardrails from settings
        for guard_name in settings.guardrails.default_guards:
            if guard_name not in self.evaluators:
                logger.warning(f"Default guard '{guard_name}' not found")
    
    def add_evaluator(self, evaluator: GuardrailEvaluator) -> None:
        """
        Add a guardrail evaluator.
        
        Args:
            evaluator: Guardrail evaluator
        """
        self.evaluators[evaluator.name] = evaluator
        logger.debug(f"Added guardrail evaluator: {evaluator.name}")
    
    def remove_evaluator(self, name: str) -> None:
        """
        Remove a guardrail evaluator.
        
        Args:
            name: Evaluator name
        """
        if name in self.evaluators:
            del self.evaluators[name]
            logger.debug(f"Removed guardrail evaluator: {name}")
    
    def is_enabled(self) -> bool:
        """
        Check if guardrails are enabled.
        
        Returns:
            True if guardrails are enabled, False otherwise
        """
        return self.enabled
    
    def enable(self) -> None:
        """Enable guardrails."""
        self.enabled = True
        logger.info("Guardrails enabled")
    
    def disable(self) -> None:
        """Disable guardrails."""
        self.enabled = False
        logger.info("Guardrails disabled")
    
    async def evaluate_chat_input(
        self,
        request: ChatCompletionRequest,
        context: Optional[Any] = None,
        evaluator_names: Optional[List[str]] = None
    ) -> bool:
        """
        Evaluate chat input against guardrails.
        
        Args:
            request: Chat completion request
            context: Additional context
            evaluator_names: Names of evaluators to use (if None, use all)
            
        Returns:
            True if input passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Skip if guardrails are disabled
        if not self.enabled:
            return True
        
        # Get evaluators to use
        evaluators = []
        if evaluator_names:
            for name in evaluator_names:
                if name in self.evaluators:
                    evaluators.append(self.evaluators[name])
                else:
                    logger.warning(f"Guardrail evaluator '{name}' not found")
        else:
            evaluators = list(self.evaluators.values())
        
        # Apply evaluators
        for evaluator in evaluators:
            await evaluator.evaluate_input(request, context)
        
        return True
    
    async def evaluate_chat_output(
        self,
        response: ChatCompletionResponse,
        context: Optional[Any] = None,
        evaluator_names: Optional[List[str]] = None
    ) -> bool:
        """
        Evaluate chat output against guardrails.
        
        Args:
            response: Chat completion response
            context: Additional context
            evaluator_names: Names of evaluators to use (if None, use all)
            
        Returns:
            True if output passes guardrails, False otherwise
            
        Raises:
            GuardrailError: If guardrails are violated
        """
        # Skip if guardrails are disabled
        if not self.enabled:
            return True
        
        # Get evaluators to use
        evaluators = []
        if evaluator_names:
            for name in evaluator_names:
                if name in self.evaluators:
                    evaluators.append(self.evaluators[name])
                else:
                    logger.warning(f"Guardrail evaluator '{name}' not found")
        else:
            evaluators = list(self.evaluators.values())
        
        # Apply evaluators
        for evaluator in evaluators:
            await evaluator.evaluate_output(response, context)
        
        return True