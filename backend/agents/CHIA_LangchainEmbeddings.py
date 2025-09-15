"""
Legacy file - use the modular structure in the agents package instead.

This file is kept for backward compatibility but the functionality has been
refactored into separate modules:

- agents.hiv_counselor: Main HIVPrEPCounselor class
- agents.rag_system: RAG functionality
- agents.teachability_manager: Conversation memory
- agents.agents: Agent definitions
- agents.function_registry: Function registration
- agents.group_chat_manager: WebSocket communication
- agents.config: Configuration and utilities
"""

# Import the main class from the new modular structure
from .hiv_counselor import HIVPrEPCounselor
from .group_chat_manager import TrackableGroupChatManager

# Re-export for backward compatibility
__all__ = ['HIVPrEPCounselor', 'TrackableGroupChatManager']
