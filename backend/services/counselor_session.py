"""
Main HIV PrEP Counselor class that orchestrates all components.
"""
import autogen
from fastapi import WebSocket

try:
    # Try absolute imports first (when running from project root)
    from backend.config import get_api_key, get_llm_config
    from backend.components.rag_system import RAGSystem
    from backend.components.teachability_manager import TeachabilityManager
    from backend.agents.agents import AgentFactory
    from backend.tools.tool_registry import FunctionRegistry
    from backend.components.group_chat_manager import TrackableGroupChatManager
except ImportError:
    # Fall back to relative imports (when running from backend directory)
    from config import get_api_key, get_llm_config
    from components.rag_system import RAGSystem
    from components.teachability_manager import TeachabilityManager
    from agents.agents import AgentFactory
    from tools.tool_registry import FunctionRegistry
    from components.group_chat_manager import TrackableGroupChatManager


class HIVPrEPCounselor:
    """Main class for HIV PrEP counseling system."""

    def __init__(self, websocket: WebSocket, user_id: str,
                 chat_id: str = None, teachability_flag: bool = None):
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
        self.agent_wrappers = AgentFactory.create_agent_wrappers(
            self.llm_config, self.teachability_flag, self.websocket)
        self.counselor_wrapper, self.assistant_wrapper, self.patient_agent = (
            self.agent_wrappers
        )

        # Get the underlying autogen agents for group chat
        # Order: patient (user), assistant (tools), counselor (final responder)
        self.agents = [
            self.patient_agent,
            self.assistant_wrapper.get_agent(),
            self.counselor_wrapper.get_agent(),
        ]
        self._setup_group_chat()
        self._register_functions()

        # Add teachability to agents
        if self.teachability_flag and self.teachability_manager.teachability:
            self.counselor_wrapper.add_teachability(self.teachability_manager)
            self.assistant_wrapper.add_teachability(self.teachability_manager)

    def _setup_group_chat(self):
        """Setup the group chat and manager."""
        # Agents order: patient (user), assistant (tools), counselor (final)

        # Configure a manager-driven group chat with explicit turn-taking
        allowed = {
            self.patient_agent: [self.assistant_wrapper.get_agent()],
            self.assistant_wrapper.get_agent(): [
                self.counselor_wrapper.get_agent()
            ],
            self.counselor_wrapper.get_agent(): [],
        }

        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
            max_round=3,  # patient -> assistant -> counselor
            allowed_or_disallowed_speaker_transitions=allowed,
            speaker_transitions_type="allowed",
        )

        self.manager = TrackableGroupChatManager(
            websocket=self.websocket,
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message=(
                "You are managing a conversation between a patient and a "
                "counselor.\n\nCONVERSATION FLOW:\n"
                "1. Patient asks a question\n"
                "2. Counselor responds with helpful information\n"
                "3. Conversation ends after counselor responds\n\n"
                "RULES:\n"
                "- Only the counselor should respond to patient messages\n"
                "- After counselor responds, conversation should end\n"
                "- Use FAQ knowledge for information unless not available\n"
            )
        )

        # Set the counselor name for filtering WebSocket messages
        counselor_name = self.counselor_wrapper.get_agent().name
        self.manager.set_counselor_name(counselor_name)

    def _register_functions(self):
        """Register all functions with the agents."""
        counselor_agent = self.counselor_wrapper.get_agent()
        assistant_agent = self.assistant_wrapper.get_agent()
        function_registry = FunctionRegistry(
            self.rag_system,
            self.teachability_manager,
            self.websocket,
            self.chat_id,
            self.patient_agent,
        )
        function_registry.register_all_functions(
            counselor_agent, assistant_agent
        )

    def get_latest_response(self):
        """Get the latest valid response, prioritizing counselor responses."""
        # This method is kept for backward compatibility but the
        # GroupChatManager now handles WebSocket communication directly
        try:
            if not self.group_chat.messages:
                print("No messages in group chat")
                return None

            # Get counselor agent name for filtering
            counselor_name = self.counselor_wrapper.get_agent().name

            # First, try to find a response from the counselor
            for i, message in enumerate(reversed(self.group_chat.messages)):
                print(f"Message {i}: {message}")

                # Check if this is a counselor message
                if isinstance(message, dict):
                    if (message.get('name') == counselor_name and
                            message.get('content')):
                        print(f"Found counselor response: "
                              f"{message['content']}")
                        return message['content']
                    elif (message.get('content') and
                          not message.get('name')):
                        # If no name specified, check if it's from counselor
                        # by position - Counselor is typically the last agent
                        continue
                elif isinstance(message, str):
                    # For string messages, we need to check if they're
                    # from counselor - This is a fallback - ideally all
                    # messages should be dicts
                    continue

            # If no counselor response found, fall back to any valid response
            for i, message in enumerate(
                    reversed(self.group_chat.messages)):
                print(f"Fallback message {i}: {message}")
                if isinstance(message, dict) and message.get('content'):
                    return message['content']
                elif isinstance(message, str):
                    print(f"Found string response: {message}")
                    return message

            print("No valid response found")
            return None
        except Exception as e:
            print(f"Error getting response: {e}")
            return None

    async def initiate_chat(self, user_input: str = None):
        """Initiate a chat session via the group chat manager."""
        if not user_input:
            return

        try:
            print(f"Initiating chat with content: '{user_input}'")

            # Have the patient agent initiate the chat with the manager.
            # This triggers orchestration and websocket streaming.
            await self.patient_agent.a_initiate_chat(
                self.manager,
                message=user_input,
                clear_history=False,
            )

            print("Chat initiation completed.")

            # Since a_run_chat is not being called, manually send the final
            # response
            await self._send_final_response_manually()
        except Exception as e:
            print(f"Chat initiation error: {e}")
            import traceback
            traceback.print_exc()

    async def _send_final_response_manually(self):
        """Manually send the final counselor response to the WebSocket."""
        if not self.websocket:
            return

        counselor_name = self.counselor_wrapper.get_agent().name
        if not counselor_name:
            return

        # Find the last message from the counselor
        for message in reversed(self.group_chat.messages):
            if (isinstance(message, dict) and
                    message.get('name') == counselor_name and
                    message.get('content')):
                formatted_message = self.manager._clean_message(
                    message['content'])
                if formatted_message:
                    await self.manager.send_message(formatted_message)
                break
        else:
            # Fallback: send the assistant's response if counselor didn't
            # respond
            for message in reversed(self.group_chat.messages):
                if (isinstance(message, dict) and
                        message.get('name') == 'counselor_assistant' and
                        message.get('content')):
                    formatted_message = self.manager._clean_message(
                        message['content'])
                    if formatted_message:
                        await self.manager.send_message(formatted_message)
                    break
