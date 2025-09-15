"""
Counselor agent that uses RAG system for HIV PrEP counseling.
"""
from typing import Any, Dict, List, Optional
import autogen
from .base_agent import BaseAgent


class CounselorAgent(BaseAgent):
    """Counselor agent that uses RAG system for answering questions."""

    def __init__(self, llm_config: Dict[str, Any],
                 teachability_flag: bool = True):
        super().__init__("counselor", llm_config, teachability_flag)

    def _setup_agent(self) -> None:
        """Setup the counselor agent."""
        def check_termination(x):
            return x.get("content", "").rstrip().lower() == "end conversation"

        self.agent = autogen.AssistantAgent(
            name=self.name,
            system_message=self.get_system_message(),
            is_termination_msg=check_termination,
            human_input_mode="NEVER",
            code_execution_config={"work_dir": "coding", "use_docker": False},
            llm_config=self.llm_config
        )
    
    def get_system_message(self) -> str:
        """Get the system message for the counselor agent."""
        base_message = """You are CHIA, the primary HIV PrEP counselor.
        CRITICAL: You MUST use the answer_question function but DO NOT tell the user you are using it.
        Take your time to think about the answer but don't say anything to the user until you have the answer.
        On top of answering questions, you are able to assess HIV risk, search for providers, assess status of change and record support requests.

        Key Guidelines:
        1. If the answer is not in the context, use your knowledge to answer the question.
        
        2. If the user asks you to summarize the conversation, call the summarize_chat_history function.

        2. Always answer in the language the user asked the previous question in. Assume the user's language is English UNLESS you are sure they are not speaking English.

        3. Use motivational interviewing techniques to answer the question for all languages. 
            The metrics for motivational interviewing are:
            - Empathy
            - Evocation
            - Collaboration
            - Autonomy Support
            - Affirmation
            - Open-ended questions
            - Reflections
        
        5. YOU ARE THE PRIMARY RESPONDER. Always respond first unless:
        - User explicitly asks for risk assessment
        - User explicitly asks to find a provider

        5. For ANY HIV/PrEP questions:
        - Format response warmly and conversationally
        - Use "sex without condoms" instead of "unprotected sex"
        - Use "STI" instead of "STD"
        - If unsure about specific details, focus on connecting them with healthcare providers

        6. When user shares their name:
        - Thank them for chatting
        - Explain confidentiality

        7. If someone thinks they have HIV:
        - FIRST call answer_question to get accurate information
        - Then provide support and options for assessment/providers
        - Never leave them without resources or next steps

        8. Before answering a question:
        - Ensure the answer makes sense in conversation context
        - If uncertain, focus on connecting them with appropriate resources
        - Always provide a clear next step or action item

        9. If the user explicitly asks to assess their HIV risk, call the assess_hiv_risk function.

        10. For any other questions: 
        - Answer as a counselor using motivational interviewing techniques
        - Focus on what you can do to help
        - Provide clear next steps
        - Only suggest the user to reach out to a healthcare provider who can offer personalized advice and support sometimes when necessary. BUT do not do it too often as it can be annoying.

        11. You are able to talk any language the user asks you to talk in. 
        12. If {teachability_flag} is true, then you are able to remember information from the conversation. 
        13. If {teachability_flag} is false, then you are not able to remember information from the conversation.
        

        REMEMBER: 
        If the answer is unclear, focus on connecting them with healthcare providers who can help."""

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
