"""
Function registry for agent tools and capabilities.
"""
import autogen
from .config import client
from tools.functions import (
    search_provider, 
    assess_ttm_stage_single_question, 
    assess_hiv_risk, 
    notify_research_assistant, 
    record_support_request, 
    translate_question
)


class FunctionRegistry:
    """Registry for managing agent functions and tools."""
    
    def __init__(self, rag_system, teachability_manager, websocket, chat_id: str = None):
        self.rag_system = rag_system
        self.teachability_manager = teachability_manager
        self.websocket = websocket
        self.chat_id = chat_id
    
    def register_all_functions(self, counselor, counselor_assistant):
        """Register all available functions with the agents."""
        self._register_answer_question(counselor, counselor_assistant)
        self._register_assess_hiv_risk(counselor, counselor_assistant)
        self._register_search_provider(counselor, counselor_assistant)
        self._register_assess_status_of_change(counselor, counselor_assistant)
        self._register_record_support_request(counselor, counselor_assistant)
        self._register_notify_research_assistant(counselor, counselor_assistant)
        
        if self.teachability_manager.teachability_flag:
            self._register_summarize_chat_history(counselor, counselor_assistant)
    
    def _register_answer_question(self, counselor, counselor_assistant):
        """Register the answer_question function."""
        def answer_question_wrapper(user_question: str) -> str:
            return self.rag_system.answer_question(user_question)
        
        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="answer_question",
            description="""Use this function to get HIV/PrEP information by passing the user's question as a parameter.
            Example: answer_question("What are the side effects of PrEP?")
            REQUIRED: Must be called before providing ANY HIV/PrEP information.""",
        )
    
    def _register_assess_hiv_risk(self, counselor, counselor_assistant):
        """Register the assess_hiv_risk function."""
        async def assess_hiv_risk_wrapper(language: str) -> str:
            result = await assess_hiv_risk(self.websocket, language)
            complete_memo = (
                "=== HIV Risk Assessment Results ===\n"
                f"Risk Level: {result}\n"
            )
            self.teachability_manager.store_memo(complete_memo)
            return result
        
        autogen.agentchat.register_function(
            assess_hiv_risk_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="assess_hiv_risk",
            description="Assesses HIV risk when the user explicitly asks for it. For the language paramter, please detect the language of the user's question and pass it as a parameter.",
        )
    
    def _register_search_provider(self, counselor, counselor_assistant):
        """Register the search_provider function."""
        def search_provider_wrapper(zip_code: str, language: str) -> str:
            return search_provider(zip_code, language)
        
        autogen.agentchat.register_function(
            search_provider_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="search_provider",
            description="Returns a list of nearby providers. After getting the zip code, immediatelyb return the list of providers. DO NOT say anythiing such as: Please wait while I search for providers. Just return the list of providers. For the language parameter, please detect the language of the user's question and pass it as a parameter.",
        )
    
    def _register_assess_status_of_change(self, counselor, counselor_assistant):
        """Register the assess_status_of_change function."""
        async def assess_status_of_change_wrapper(language: str) -> str:
            return await assess_ttm_stage_single_question(self.websocket, language)
        
        autogen.agentchat.register_function(
            assess_status_of_change_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="assess_status_of_change",
            description="Assesses the status of change for the patient. For the language parameter, please detect the language of the user's question and pass it as a parameter.",
        )
    
    def _register_record_support_request(self, counselor, counselor_assistant):
        """Register the record_support_request function."""
        async def record_support_request_wrapper(language: str) -> str:
            return await record_support_request(self.websocket, self.chat_id, language)
        
        autogen.agentchat.register_function(
            record_support_request_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="record_support_request",
            description="""Do not immediately call this function.
            Wait for the user to show signs of distress over time (DO NOT ACTIVATE THE FIRST TIME) or requests human support.
            For example, if the user suggests that they want 
            First ask if they are sure they want human support. 
            If they do, then call this function. If they don't, then do not call this function.
            For the language parameter, please detect the language of the user's question and pass it as a parameter.""",
        )
    
    def _register_notify_research_assistant(self, counselor, counselor_assistant):
        """Register the notify_research_assistant function."""
        async def notify_research_assistant_wrapper(language: str) -> str:
            return await notify_research_assistant(self.websocket, language)
        
        autogen.agentchat.register_function(
            notify_research_assistant_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="notify_research_assistant",
            description="""Notify the research assistant when the user is ready to be contacted.
            """,
        )
    
    def _register_summarize_chat_history(self, counselor, counselor_assistant):
        """Register the summarize_chat_history function."""
        def summarize_chat_history_wrapper(user_request: str, language: str = "English") -> str:
            if not self.teachability_manager.teachability_flag:
                return "I apologize, but I couldn't find any chat history to summarize. The teachability feature is not enabled."
            
            try:
                # Get all memos from the store
                memos = self.teachability_manager.get_related_memos(user_request, n_results=200, threshold=10.0)
                if not memos:
                    return "I apologize, but I couldn't find any previous conversations to summarize."
                
                # Format the memos into a readable string
                memo_text = "\n".join([f"Conversation: {memo[1]}\nResponse: {memo[2]}" for memo in memos])
                
                # Create messages for OpenAI
                messages = [
                    {"role": "system", "content": """You are a helpful assistant that summarizes chat history in a natural, conversational way.
                    Please provide a comprehensive summary of the conversations, highlighting key topics discussed and any important information shared.
                    Focus on the main themes and important details from the conversations.
                    Make the summary sound natural and conversational, as if you're recalling the conversation from memory."""},
                    {"role": "user", "content": f"Here are the previous conversations:\n{memo_text}\n\nPlease summarize these conversations based on this request: {user_request}"}
                ]
                
                # Call OpenAI API
                chat_completion = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                if not chat_completion or not chat_completion.choices:
                    return "I apologize, but I couldn't generate a summary of the chat history."
                
                return translate_question(chat_completion.choices[0].message.content, language)
                
            except Exception as e:
                print(f"Error summarizing chat history: {e}")
                return "I apologize, but I encountered an error while trying to summarize our previous conversations."
        
        autogen.agentchat.register_function(
            summarize_chat_history_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="summarize_chat_history",
            description="""Summarizes all previous conversations stored in the teachability system, 
            including risk assessments, provider searches, status changes, and support requests.
             For the language parameter, please detect the language of the user's question and pass it as a parameter.""",
        )
