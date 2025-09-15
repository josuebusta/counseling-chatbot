"""
Components package for the HIV PrEP Counseling System.

This package contains the core components used by the main orchestrator:
- RAGSystem: Retrieval-Augmented Generation for knowledge base queries
- TeachabilityManager: Conversation memory and learning capabilities
- TrackableGroupChatManager: WebSocket communication and message handling
"""

from .rag_system import RAGSystem
from .teachability_manager import TeachabilityManager
from .group_chat_manager import TrackableGroupChatManager

__all__ = [
    'RAGSystem',
    'TeachabilityManager',
    'TrackableGroupChatManager'
]

__version__ = "1.0.0"
