"""
Core models implementation for the AI Gateway.
"""
from typing import Dict, List, Optional, Any, Set
import yaml
import os
from pathlib import Path
import logging
from pydantic import ValidationError

from gateway.config.models import ModelDefinition


logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing available models in the AI Gateway.
    Handles loading model definitions from YAML files and provides access to model metadata.
    """
    
    def __init__(self) -> None:
        self._models: Dict[str, ModelDefinition] = {}
        self._loaded = False

    def load_models(self, models_path: Optional[str] = None, force_reload: bool = False) -> List[ModelDefinition]:
        """
        Load model definitions from YAML files.
        
        Args:
            models_path: Path to the directory or file containing model definitions.
                         If None, will use the default path.
            force_reload: Whether to force reload even if models are already loaded.
            
        Returns:
            List of loaded model definitions.
        """
        if self._loaded and not force_reload:
            return list(self._models.values())
        
        # Default models path relative to current file
        if not models_path:
            current_dir = Path(__file__).parent.parent.parent
            models_path = current_dir / "models.yaml"
        
        path = Path(models_path)
        
        if not path.exists():
            logger.warning(f"Models path does not exist: {path}")
            return []
        
        # Clear existing models if reloading
        self._models = {}
        
        try:
            if path.is_file():
                self._load_models_from_file(path)
            elif path.is_dir():
                for file in path.glob("*.yaml"):
                    self._load_models_from_file(file)
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return []
        
        self._loaded = True
        logger.info(f"Loaded {len(self._models)} models")
        return list(self._models.values())
    
    def _load_models_from_file(self, file_path: Path) -> None:
        """
        Load model definitions from a single YAML file.
        
        Args:
            file_path: Path to the YAML file.
        """
        try:
            with open(file_path, "r") as f:
                models_data = yaml.safe_load(f)
            
            if not isinstance(models_data, list):
                logger.warning(f"Invalid models file format: {file_path}. Expected a list.")
                return
            
            for model_data in models_data:
                try:
                    model = ModelDefinition.model_validate(model_data)
                    self._models[model.model] = model
                    logger.debug(f"Loaded model: {model.model}")
                except ValidationError as e:
                    logger.warning(f"Invalid model definition in {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"Error loading models from {file_path}: {e}")
    
    def get_model(self, model_id: str) -> Optional[ModelDefinition]:
        """
        Get a model definition by ID.
        
        Args:
            model_id: ID of the model to retrieve.
            
        Returns:
            ModelDefinition if found, None otherwise.
        """
        if not self._loaded:
            self.load_models()
        
        return self._models.get(model_id)
    
    def list_models(self) -> List[ModelDefinition]:
        """
        List all available models.
        
        Returns:
            List of all model definitions.
        """
        if not self._loaded:
            self.load_models()
        
        return list(self._models.values())
    
    def get_models_by_type(self, model_type: str) -> List[ModelDefinition]:
        """
        Get models by type.
        
        Args:
            model_type: Type of models to retrieve.
            
        Returns:
            List of model definitions matching the type.
        """
        if not self._loaded:
            self.load_models()
        
        return [
            model for model in self._models.values()
            if model.type == model_type
        ]
    
    def get_provider_models(self, provider: str) -> List[ModelDefinition]:
        """
        Get models by provider.
        
        Args:
            provider: Provider name.
            
        Returns:
            List of model definitions from the specified provider.
        """
        if not self._loaded:
            self.load_models()
        
        return [
            model for model in self._models.values()
            if model.inference_provider.provider == provider
        ]
    
    def get_capabilities(self, model_id: str) -> Set[str]:
        """
        Get capabilities of a specific model.
        
        Args:
            model_id: ID of the model.
            
        Returns:
            Set of capability strings.
        """
        model = self.get_model(model_id)
        if not model:
            return set()
        
        return set(capability.value for capability in model.capabilities)
    
    def get_parameter_schema(self, model_id: str) -> Dict[str, Any]:
        """
        Get parameter schema for a specific model.
        
        Args:
            model_id: ID of the model.
            
        Returns:
            Dictionary representing the parameter schema.
        """
        model = self.get_model(model_id)
        if not model or not model.parameters:
            return {}
        
        return {name: param.model_dump() for name, param in model.parameters.items()}


# Global model registry instance
model_registry = ModelRegistry()