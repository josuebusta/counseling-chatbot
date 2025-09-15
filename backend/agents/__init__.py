"""
HIV PrEP Counseling System

A modular system for providing HIV PrEP counseling through AI agents with RAG
teachability features, and WebSocket communication.

Main Components:
- HIVPrEPCounselor: Main orchestrator class
- RAGSystem: Retrieval-Augmented Generation for knowledge base queries
- TeachabilityManager: Conversation memory and learning
- AgentFactory: Creates different types of agents
- FunctionRegistry: Manages agent tools and capabilities
- TrackableGroupChatManager: WebSocket communication handler
"""

from components.rag_system import RAGSystem
from components.teachability_manager import TeachabilityManager
from .agents import AgentFactory
from tools.tool_registry import FunctionRegistry
from components.group_chat_manager import TrackableGroupChatManager
from .base_agent import BaseAgent
from .counselor_agent import CounselorAgent
from .assistant_agent import AssistantAgent
from config import get_api_key, get_llm_config, DEFAULT_CONFIG, client

__all__ = [
    'RAGSystem',
    'TeachabilityManager',
    'AgentFactory',
    'FunctionRegistry',
    'TrackableGroupChatManager',
    'BaseAgent',
    'CounselorAgent',
    'AssistantAgent',
    'get_api_key',
    'get_llm_config',
    'DEFAULT_CONFIG',
    'client'
]

__version__ = "1.0.0"
