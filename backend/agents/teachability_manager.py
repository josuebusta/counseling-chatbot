"""
Teachability manager for storing and retrieving conversation memories.
"""
import os
from autogen.agentchat.contrib.capabilities.teachability import Teachability
from .config import DEFAULT_CONFIG
from .database_config import get_user_teachability_path


class TeachabilityManager:
    """Manages conversation memory and teachability features."""
    
    def __init__(self, user_id: str, teachability_flag: bool = True, llm_config: dict = None):
        self.user_id = user_id
        self.teachability_flag = teachability_flag
        self.teachability = None
        
        if self.teachability_flag and llm_config:
            self._initialize_teachability(llm_config)
    
    def _initialize_teachability(self, llm_config: dict):
        """Initialize teachability components."""
        # Use centralized database path configuration
        user_db_path = get_user_teachability_path(self.user_id)
        
        print(f"DEBUG: llm_config being passed to Teachability: {llm_config}")
        print(f"DEBUG: API key in config_list: {llm_config.get('config_list', [{}])[0].get('api_key', 'NOT_FOUND')[:10]}...")
        
        self.teachability = Teachability(
            reset_db=False, 
            path_to_db_dir=user_db_path,
            recall_threshold=DEFAULT_CONFIG["recall_threshold"],
            verbosity=DEFAULT_CONFIG["verbosity"],
            llm_config=llm_config
        )
        print(f"Teachability initialized with path: {user_db_path}")
    
    def add_to_agent(self, agent):
        """Add teachability to an agent."""
        if self.teachability_flag and self.teachability:
            self.teachability.add_to_agent(agent)
    
    def store_memo(self, memo: str):
        """Store a memo in the teachability system."""
        if self.teachability_flag and self.teachability:
            self.teachability._consider_memo_storage(memo)
    
    def get_related_memos(self, query: str, n_results: int = 200, threshold: float = 10.0):
        """Get related memos from the teachability system."""
        if not self.teachability_flag or not self.teachability:
            return []
        
        return self.teachability.memo_store.get_related_memos(query, n_results, threshold)
