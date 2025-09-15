"""
Assistant agent that uses function registry for specialized tasks.
"""
from typing import Any, Dict, List, Optional
import autogen
from .base_agent import BaseAgent


class AssistantAgent(BaseAgent):
    """Assistant agent that uses function registry for specialized tasks."""

    def __init__(self, llm_config: Dict[str, Any],
                 teachability_flag: bool = True):
        super().__init__("counselor_assistant", llm_config, teachability_flag)

    def _setup_agent(self) -> None:
        """Setup the assistant agent."""
        def check_termination(x):
            return x.get("content", "").rstrip().lower() == "end conversation"

        self.agent = autogen.AssistantAgent(
            name=self.name,
            system_message=self.get_system_message(),
            is_termination_msg=check_termination,
            human_input_mode="NEVER",
            llm_config=self.llm_config
        )

    def get_system_message(self) -> str:
        """Get the system message for the assistant agent."""
        base_message = (
            "You are CHIA's Assistant, a tool-orchestrating agent that "
            "supports the primary Counselor for HIV PrEP.\n"
            "Your role is to plan and invoke functions to gather accurate "
            "information and structured results.\n"
            "You are NOT the primary responder and should not speak directly "
            "to the user. Instead, use tools and provide results for the "
            "Counselor to deliver.\n\n"
            "Core responsibilities:\n"
            "- Decide which function(s) to call based on the user's latest "
            "message and conversation context.\n"
            "- Prefer calling answer_question first for HIV/PrEP information "
            "needs.\n"
            "- For explicit requests, call specialized tools: \n"
            "  assess_hiv_risk, search_provider, assess_status_of_change, \n"
            "  record_support_request, summarize_chat_history,\n"
            "  notify_research_assistant.\n"
            "- CRITICAL for search_provider: You MUST first ask the user for their "
            "ZIP code before calling this function. Do not call it with placeholder text.\n"
            "- Do not reveal tool internals; simply return results to enable "
            "the Counselor's response.\n\n"
            "Language & context:\n"
            "- Detect the user's language and pass it to tools that require "
            "a language parameter.\n"
            "- Maintain consistency with conversation context; avoid "
            "redundant or conflicting tool calls.\n\n"
            "Safety & style guardrails for tool usage:\n"
            "- Use \"sex without condoms\" instead of \"unprotected sex\" and "
            "\"STI\" instead of \"STD\" when generating or selecting tool "
            "prompts.\n"
            "- If information is uncertain or outside retrieved context, "
            "proceed with the best available tool-assisted guidance; avoid "
            "fabricating facts.\n\n"
            "Memory (teachability):\n"
            "- If {teachability_flag} is true, you may store or retrieve "
            "memos via registered functions to help the Counselor summarize "
            "or recall.\n"
            "- If {teachability_flag} is false, do not rely on conversational "
            "memory.\n"
        )

        return base_message.format(teachability_flag=self.teachability_flag)

    async def respond(self, messages: List[Dict[str, Any]],
                      sender: Optional[Any] = None) -> str:
        """Generate a response to the given messages."""
        try:
            response = await self.agent.a_generate_reply(
                messages=messages,
                sender=sender,
                config=self.agent
            )
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
            return ("I apologize, but I encountered an error while "
                    "processing your request.")

    def respond_sync(self, messages: List[Dict[str, Any]],
                     sender: Optional[Any] = None) -> str:
        """Synchronous version of respond for compatibility."""
        try:
            response = self.agent.generate_reply(
                messages=messages,
                sender=sender,
                config=self.agent
            )
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
            return ("I apologize, but I encountered an error while "
                    "processing your request.")
