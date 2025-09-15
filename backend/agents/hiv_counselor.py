"""
Main HIV PrEP Counselor class that orchestrates all components.
"""
import autogen
from fastapi import WebSocket

from .config import get_api_key, get_llm_config, DEFAULT_CONFIG
from .rag_system import RAGSystem
from .teachability_manager import TeachabilityManager
from .agents import AgentFactory
from .function_registry import FunctionRegistry
from .group_chat_manager import TrackableGroupChatManager


class HIVPrEPCounselor:
    """Main class for HIV PrEP counseling system."""
    
    def __init__(self, websocket: WebSocket, user_id: str, chat_id: str = None, teachability_flag: bool = None):
        self.user_id = user_id
        self.chat_id = chat_id 
        self.teachability_flag = teachability_flag
        if self.teachability_flag is None:
            self.teachability_flag = True
        print(f"[INIT] Teachability flag set to: {self.teachability_flag}")
        print("chat_id", self.chat_id)
        
        self.api_key = get_api_key()
        self.websocket = websocket
        self.agent_history = []
        
        # Initialize components
        self.llm_config = get_llm_config(self.api_key)
        self.rag_system = RAGSystem(self.api_key)
        self.teachability_manager = TeachabilityManager(
            self.user_id, 
            self.teachability_flag, 
            self.llm_config
        )
        
        # Initialize agents and group chat
        self.agents = AgentFactory.create_all_agents(self.llm_config, self.teachability_flag)
        self._setup_group_chat()
        self._register_functions()
        
        # Add teachability to agents
        if self.teachability_flag and self.teachability_manager.teachability:
            self.teachability_manager.add_to_agent(self.agents[0])  # counselor
            self.teachability_manager.add_to_agent(self.agents[2])  # counselor_assistant

    def _setup_group_chat(self):
        """Setup the group chat and manager."""
        counselor, patient, counselor_assistant = self.agents
        
        speaker_transitions = {
            counselor: [counselor_assistant, counselor],
            counselor_assistant: [counselor, counselor_assistant],
            patient: []
        }
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
            max_round=DEFAULT_CONFIG["max_rounds"],
            allowed_or_disallowed_speaker_transitions=speaker_transitions,
            speaker_transitions_type="disallowed"
        )

        self.manager = TrackableGroupChatManager(
            websocket=self.websocket,
            groupchat=self.group_chat, 
            llm_config=self.llm_config,
            system_message="""Ensure counselor is primary responder. It should ALWAYS use FAQ agent's 
            knowledge for information unless the information is not available. Only use assessment_bot and search_bot for 
            explicit requests.
            
                1. Only one agent should respond to each user message
                2. After an agent responds, wait for the user's next message
                3. Never have multiple agents respond to the same user message,
                4. Ensure counselor responds first using FAQ agent's knowledge, 
                unless explicitly asked for risk assessment or provider search
                """
        )

    def _register_functions(self):
        """Register all functions with the agents."""
        counselor, patient, counselor_assistant = self.agents
        function_registry = FunctionRegistry(
            self.rag_system, 
            self.teachability_manager, 
            self.websocket, 
            self.chat_id
        )
        function_registry.register_all_functions(counselor, counselor_assistant)

    def get_latest_response(self):
        """Get the latest valid response."""
        try:
            if not self.group_chat.messages:
                return None
                
            for message in reversed(self.group_chat.messages):
                if isinstance(message, dict) and message.get('content'):
                    return message['content']
                elif isinstance(message, str):
                    return message
                    
            return None
        except Exception as e:
            print(f"Error getting response: {e}")
            return None

    async def initiate_chat(self, user_input: str = None):
        """Initiate a chat session with the user input."""
        if not user_input:
            return

        try:
            print(f"Initiating chat with content: '{user_input}'")
            # agents[1] is the patient agent
            await self.agents[1].a_initiate_chat(
                recipient=self.manager,
                message=str(user_input),
                clear_history=False,
                system_message="""Ensure counselor responds first using FAQ agent's knowledge, 
                unless explicitly asked for risk assessment or provider search.  Ensure only one agent responds per turn. """
            )
            print("a_initiate_chat completed.")
        except Exception as e:
            print(f"Chat initiation error: {e}")
            import traceback
            traceback.print_exc()
