"""
HIV PrEP Counseling System

A modular system for providing HIV PrEP counseling through AI agents with RAG capabilities,
teachability features, and WebSocket communication.

Main Components:
- HIVPrEPCounselor: Main orchestrator class
- RAGSystem: Retrieval-Augmented Generation for knowledge base queries
- TeachabilityManager: Conversation memory and learning
- AgentFactory: Creates different types of agents
- FunctionRegistry: Manages agent tools and capabilities
- TrackableGroupChatManager: WebSocket communication handler
"""

from .hiv_counselor import HIVPrEPCounselor
from .rag_system import RAGSystem
from .teachability_manager import TeachabilityManager
from .agents import AgentFactory
from .function_registry import FunctionRegistry
from .group_chat_manager import TrackableGroupChatManager
from .config import get_api_key, get_llm_config, DEFAULT_CONFIG, client

__all__ = [
    'HIVPrEPCounselor',
    'RAGSystem', 
    'TeachabilityManager',
    'AgentFactory',
    'FunctionRegistry',
    'TrackableGroupChatManager',
    'get_api_key',
    'get_llm_config',
    'DEFAULT_CONFIG',
    'client'
]

__version__ = "1.0.0"
