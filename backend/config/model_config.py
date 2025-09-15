"""
Model configuration management for different agents.
"""
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ModelConfig:
    """Manages model configurations for different agents."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize model configuration.

        Args:
            config_path: Path to the YAML configuration file.
                        Defaults to model_config.yaml in the same directory.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "model_config.yaml"

        self.config_path = config_path
        self._config = None
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")

    def get_config(self, agent_name: str = "default") -> Dict[str, Any]:
        """Get configuration for a specific agent.

        Args:
            agent_name: Name of the agent to get configuration for.

        Returns:
            Dictionary containing the agent's configuration.
        """
        if agent_name not in self._config:
            raise ValueError(
                f"Configuration for agent '{agent_name}' not found"
            )

        return self._config[agent_name]

    def get_llm_config(self, agent_name: str = "default") -> Dict[str, Any]:
        """Get LLM configuration for a specific agent.

        Args:
            agent_name: Name of the agent to get LLM configuration for.

        Returns:
            Dictionary containing LLM configuration suitable for AutoGen.
        """
        agent_config = self.get_config(agent_name)

        # Extract LLM-specific parameters
        llm_config = {
            "model": agent_config.get("model", "gpt-4o"),
            "temperature": agent_config.get("temperature", 0.7),
            "max_tokens": agent_config.get("max_tokens", 4000),
            "top_p": agent_config.get("top_p", 1.0),
            "frequency_penalty": agent_config.get("frequency_penalty", 0.0),
            "presence_penalty": agent_config.get("presence_penalty", 0.0),
        }

        return llm_config

    def get_system_message(self, agent_name: str = "default") -> str:
        """Get system message for a specific agent.

        Args:
            agent_name: Name of the agent to get system message for.

        Returns:
            System message string for the agent.
        """
        agent_config = self.get_config(agent_name)
        return agent_config.get("system_message", "")

    def get_embedding_config(self) -> Dict[str, Any]:
        """Get embedding model configuration.

        Returns:
            Dictionary containing embedding configuration.
        """
        return self._config.get("embeddings", {})

    def get_retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration.

        Returns:
            Dictionary containing retrieval configuration.
        """
        return self._config.get("retrieval", {})

    def get_conversation_config(self) -> Dict[str, Any]:
        """Get conversation flow configuration.

        Returns:
            Dictionary containing conversation configuration.
        """
        return self._config.get("conversation", {})

    def get_agent_specific_config(self, agent_name: str) -> Dict[str, Any]:
        """Get agent-specific configuration.

        Args:
            agent_name: Name of the agent.

        Returns:
            Dictionary containing agent-specific configuration.
        """
        agents_config = self._config.get("agents", {})
        return agents_config.get(agent_name, {})

    def reload_config(self):
        """Reload configuration from file."""
        self._load_config()

    def get_all_agents(self) -> list:
        """Get list of all available agent names.

        Returns:
            List of agent names.
        """
        return list(self._config.keys())


# Global model configuration instance
model_config = ModelConfig()
