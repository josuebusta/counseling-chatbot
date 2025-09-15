"""
Abstract base class for all agents in the HIV PrEP counseling system.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import autogen


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, name: str, llm_config: Dict[str, Any],
                 teachability_flag: bool = True):
        self.name = name
        self.llm_config = llm_config
        self.teachability_flag = teachability_flag
        self.agent = None
        self._setup_agent()

    @abstractmethod
    def _setup_agent(self) -> None:
        """Setup the specific agent implementation."""
        pass

    @abstractmethod
    def respond(self, messages: List[Dict[str, Any]],
                sender: Optional[Any] = None) -> str:
        """Generate a response to the given messages."""
        pass

    @abstractmethod
    def get_system_message(self) -> str:
        """Get the system message for this agent."""
        pass

    def get_agent(self) -> autogen.Agent:
        """Get the underlying autogen agent."""
        return self.agent

    def add_function(self, function, name: str, description: str,
                     caller: Optional[Any] = None,
                     executor: Optional[Any] = None):
        """Add a function to the agent."""
        if caller is None:
            caller = self.agent
        if executor is None:
            executor = self.agent

        autogen.agentchat.register_function(
            function,
            caller=caller,
            executor=executor,
            name=name,
            description=description
        )

    def add_teachability(self, teachability_manager):
        """Add teachability capabilities to the agent."""
        if self.teachability_flag and teachability_manager.teachability:
            teachability_manager.add_to_agent(self.agent)
