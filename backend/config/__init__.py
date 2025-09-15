"""
Configuration package for the HIV PrEP Counselor system.
"""
from .settings import settings, Settings
from .model_config import ModelConfig

# Create model_config instance
model_config = ModelConfig()

# Backward compatibility exports
client = settings.openai_client

# Default configuration (for backward compatibility)
DEFAULT_CONFIG = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "retrieval_k": 3,
    "max_rounds": 12,
    "recall_threshold": 2.5,
    "verbosity": 1
}

def get_api_key():
    """Get OpenAI API key from environment."""
    return settings.api_key

def get_llm_config(api_key: str = None, temperature: float = 0.7, agent_name: str = "default"):
    """Create LLM configuration for agents.
    
    Args:
        api_key: OpenAI API key. If None, uses the one from settings.
        temperature: Temperature for the model. If None, uses agent-specific config.
        agent_name: Name of the agent to get configuration for.
    
    Returns:
        Dictionary containing LLM configuration for AutoGen.
    """
    if api_key is None:
        api_key = settings.api_key
    
    # Get agent-specific configuration
    agent_config = model_config.get_llm_config(agent_name)
    
    # Override temperature if provided
    if temperature != 0.7:
        agent_config["temperature"] = temperature
    
    config_list = [{
        "model": agent_config["model"],
        "api_key": api_key
    }]

    return {
        "config_list": config_list,
        "temperature": agent_config["temperature"],
        "max_tokens": agent_config.get("max_tokens", 4000),
        "top_p": agent_config.get("top_p", 1.0),
        "frequency_penalty": agent_config.get("frequency_penalty", 0.0),
        "presence_penalty": agent_config.get("presence_penalty", 0.0),
    }

__all__ = [
    'settings', 
    'Settings', 
    'ModelConfig', 
    'model_config',
    'client',
    'DEFAULT_CONFIG',
    'get_api_key',
    'get_llm_config'
]
