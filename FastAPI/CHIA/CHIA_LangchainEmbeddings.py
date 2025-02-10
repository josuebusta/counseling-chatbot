# from semantic_kernel import Kernel
# from semantic_kernel.functions.kernel_arguments import KernelArguments

# from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIChatPromptExecutionSettings
# from semantic_kernel.contents.chat_history import ChatHistory
# from semantic_kernel.prompt_template.prompt_template_config import PromptTemplateConfig
# from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
# from .function_class import HIVHelperFunctions

# from fastapi import WebSocket
# from dotenv import load_dotenv
# import os
# from .functions import search_provider, assess_ttm_stage_single_question, assess_hiv_risk, record_support_request
# import json

# class HIVPrEPCounselor:
#     def __init__(self, websocket: WebSocket, user_id: str, chat_id: str = None):
#         load_dotenv()
#         self.user_id = user_id
#         self.chat_id = chat_id
#         self.api_key = os.getenv('OPENAI_API_KEY')
#         self.websocket = websocket
#         self.history = ChatHistory()

#         print("history initialized")

#         # Load chat history from persistent storage if it exists
#         if self.chat_id:
#             self.load_chat_history()

#         # Add system message to set the context if chat history is empty
#         if not self.history.messages:
#             self.history.add_system_message(
#                 """You are CHIA, a compassionate HIV PrEP counselor. 
#                 Follow these guidelines:
#                 1. Be warm and supportive
#                 2. Use "sex without condoms" instead of "unprotected sex"
#                 3. Use "STI" instead of "STD"
#                 4. Maintain confidentiality
#                 5. Check knowledge base before providing information
#                 6. Assess risk only when explicitly requested
#                 7. Ask for ZIP code before searching providers"""
#             )

#         print("system message added to history")

#         if not self.api_key:
#             raise ValueError("API key not found. Please set OPENAI_API_KEY in .env file.")

#         # Initialize Semantic Kernel
#         self.kernel = Kernel()
#         self.setup_ai_service()
    
#     def load_chat_history(self):
#         """Load previous chat history from persistent storage"""
#         try:
#             with open(f"chat_history_{self.chat_id}.json", "r") as file:
#                 history_data = json.load(file)
#                 self.history.messages = history_data.get('messages', [])
#                 print("Chat history loaded")
#         except FileNotFoundError:
#             print("No previous chat history found for this chat_id.")
    
#     def save_chat_history(self):
#         """Save chat history to persistent storage"""
#         try:
#             with open(f"chat_history_{self.chat_id}.json", "w") as file:
#                 json.dump({"messages": [message.to_dict() for message in self.history.messages]}, file)
#             print("Chat history saved")
#         except Exception as e:
#             print(f"Error saving chat history: {e}")

#     def setup_ai_service(self):
#         """Initialize the AI service with OpenAI"""
#         self.kernel.add_service(
#             OpenAIChatCompletion(
#                 service_id="chat_completion",
#                 ai_model_id="gpt-4o-mini",
#                 api_key=self.api_key
#             )
#         )

#         # Register functions with the kernel
#         self.kernel.add_plugin(HIVHelperFunctions(), plugin_name="hiv_prep")
    
#     async def send_message(self, message: str):
#         """Send message to websocket with error handling"""
#         try:
#             if message:
#                 await self.websocket.send_text(message)
#         except Exception as e:
#             print(f"Error sending message: {e}")

#     async def process_message(self, user_input: str):
#         """Process user input and generate response"""
#         try:
#             # Add user input to history
#             self.history.add_user_message(user_input)

#             # Create execution settings
#             execution_settings = OpenAIChatPromptExecutionSettings(
#                 temperature=0.7,
#                 top_p=1.0,
#                 max_tokens=800
#             )
#             execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

#             # Get chat completion service
#             chat_completion: OpenAIChatCompletion = self.kernel.get_service("chat_completion")

#             # Get response from AI
#             response = await chat_completion.get_chat_message_content(
#                 chat_history=self.history,
#                 settings=execution_settings,
#                 kernel=self.kernel,
#                 arguments=KernelArguments()
#             )

#             # Extract and format the response
#             if response:
#                 message_content = str(response).strip()
#                 if message_content:
#                     # Add response to history
#                     self.history.add_message({"role": "assistant", "content": message_content})
                    
#                     # Send response through websocket
#                     await self.send_message(message_content)

#                     # Save the chat history after each message
#                     self.save_chat_history()
#             else:
#                 await self.send_message("I apologize, but I wasn't able to generate a response. Please try again.")

#         except Exception as e:
#             print(f"Error processing message: {e}")
#             try:
#                 await self.send_message("I apologize, but I encountered an error. Please try again.")
#             except Exception as websocket_error:
#                 print(f"Error sending error message: {websocket_error}")

#     async def initiate_chat(self, message: str):
#         """Start the chat session"""
#         try:
#             if message.lower() == "exit":
#                 return

#             # Process the initial message from the user
#             await self.process_message(message)

#             # Now wait for the user to send a response before continuing
#             while True:
#                 new_message = await self.websocket.receive_text()  # Assuming you're getting the message through WebSocket
#                 if new_message.lower() == "exit":
#                     break
#                 await self.process_message(new_message)

#         except Exception as e:
#             print(f"Chat error: {e}")
#             raise


from dotenv import load_dotenv
import json
from langchain_community.document_loaders import DirectoryLoader, JSONLoader, WebBaseLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain import hub
import autogen
from langchain.tools import BaseTool, StructuredTool, Tool, tool
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import os
from autogen.agentchat.contrib.capabilities.teachability import Teachability
from .functions import search_provider, assess_ttm_stage_single_question, assess_hiv_risk, notify_research_assistant, record_support_request
import time
import hashlib
from typing import Set, Dict, Optional

# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class TrackableGroupChatManager(autogen.GroupChatManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_message = None
        self._message_history = set()

    # def _process_received_message(self, message, sender, silent):
    #     if self.websocket:
    #         # formatted_message = self._format_message(message, sender)
    #         # if formatted_message and formatted_message not in self._message_history:  
    #         asyncio.create_task(self.send_message(message))
    #         self._message_history.add(message)
    #     return super()._process_received_message(message, sender, silent)

    def _format_message(self, message, sender) -> str:
        """Format the message for display, handling various message types"""
        try:
       
            if isinstance(message, dict):
                if 'function_call' in message or 'tool_calls' in message:
                    return None
                
                if 'content' in message and message['content']:
                    return self._clean_message(message['content'])
                
                if 'role' in message and message['role'] == 'tool':
                    if 'content' in message:
                        return self._clean_message(message['content'])
                    
            elif isinstance(message, str) and message.strip():
                return self._clean_message(message)
                
            return None
        except Exception as e:
            print(f"Error formatting message: {e}")
            return None

    def _clean_message(self, message: str) -> str:
        """Clean and format message content"""
        # Remove any existing prefixes
        prefixes = ["counselor:", "CHIA:", "assessment_bot:"]
        message = message.strip()

        for prefix in prefixes:
            if message.lower().startswith(prefix.lower()):
                message = message[len(prefix):].strip()
        return message

    async def send_message(self, message: str):
        """Send message to websocket, avoiding duplicates"""
        if message and message != self._last_message:
            try:
                await self.websocket.send_text(message)
                self._last_message = message
            except Exception as e:
                print(f"Error sending message: {e}")

    def _process_received_message(self, message, sender, silent):
        """Process and deduplicate messages"""
        if self.websocket:
            formatted_message = self._format_message(message, sender)
            if formatted_message:
                # message_hash = self._calculate_message_hash(formatted_message, sender.name)
                
                # if not self._is_duplicate(message_hash):
                #     self._message_timestamps[message_hash] = time.time()
                #     self._message_history.add(message_hash)
                asyncio.create_task(self.send_message(formatted_message))

        return super()._process_received_message(message, sender, silent)

    async def send_message(self, message: str):
        """Send message to websocket with deduplication"""
        try:
            if message and message != self._last_message:
                await self.websocket.send_text(message)
                self._last_message = message
        except Exception as e:
            print(f"Error sending message: {e}")



class HIVPrEPCounselor:
    def __init__(self, websocket: WebSocket, user_id: str, chat_id: str = None):
        load_dotenv()
        self.user_id = user_id
        self.chat_id = chat_id 
        print("chat_id", self.chat_id)
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.websocket = websocket

        if not self.api_key:
            raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

        self.config_list = {
            "model": "gpt-4",
            "api_key": self.api_key
        }

        self.agent_history = []
        self.setup_rag()
        self.initialize_agents()

    def check_termination(self, x):
        return x.get("content", "").rstrip().lower() == "end conversation"

    def setup_rag(self):
        prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")
        loader = WebBaseLoader("https://github.com/amarisg25/embedding-data-chatbot/blob/main/HIV_PrEP_knowledge_embedding.json")
        data = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_splits = text_splitter.split_documents(data)
        vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(openai_api_key=self.api_key))
        llm = ChatOpenAI(model_name="gpt-4", temperature=0)
        retriever = vectorstore.as_retriever()
        self.qa_chain = RetrievalQA.from_chain_type(
            llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
        )

    def answer_question(self, question: str) -> str:
        self.result = self.qa_chain.invoke({"query": question})
        return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

    def initialize_agents(self):
        counselor_system_message = """You are CHIA, the primary HIV PrEP counselor.
        CRITICAL: You MUST use the answer_question but DO NOT tell the user you are using it.
        Take your time to think about the answer but don't say anything to the user until you have the answer.
        The most important and commonly used function is answer_question. 

        Example workflow:
        1. When user asks about HIV/PrEP:
        - FIRST call: answer_question(user's question)
        - THEN use that response to form your answer
        2. NEVER answer without calling answer_question first

        Key Guidelines:
        1. YOU ARE THE PRIMARY RESPONDER. Always respond first unless:
        - User explicitly asks for risk assessment
        - User explicitly asks to find a provider

        2. For ANY HIV/PrEP questions:
        - MUST call answer_question function FIRST
        - Then format response warmly and conversationally
        - Use "sex without condoms" instead of "unprotected sex"
        - Use "STI" instead of "STD"

        3. When user shares their name:
        - Thank them for chatting
        - Explain confidentiality

        4. Let specialized tools handle ONLY:
        - HIV risk assessment (when explicitly requested)
        - Provider search (when explicitly requested)

        5. If someone thinks they have HIV:
        - FIRST call answer_question to get accurate information
        - Then provide support and options for assessment/providers

        6. Before answering a question, make sure the answer makes sense with the context of the conversation.
            For example, if the user says "I need help," do not directly assume they need help with PrEP...

        7. Never call the request support function before asking if they are sure they want human support.
           - This step is **EXTREMELY IMPORTANT** to ensure users understand they are transitioning to human support.
           - Confirm their intent before proceeding.

        8. For any other questions, answer as a counselor using motivational interviewing techniques.

        REMEMBER: ALWAYS call answer_question before providing ANY HIV/PrEP information"""

        patient = autogen.UserProxyAgent(
            name="patient",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=10,
            code_execution_config={"work_dir": "coding", "use_docker": False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message=counselor_system_message,
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        counselor_assistant = autogen.AssistantAgent(
            name="counselor_assistant",
            system_message=counselor_system_message,
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            llm_config=self.config_list,
            websocket=self.websocket
        )

                
        self.agents = [counselor,patient, counselor_assistant]

        def answer_question_wrapper(user_question: str) -> str:
            return self.answer_question(user_question)
        
        async def assess_hiv_risk_wrapper() -> str:
            response = await assess_hiv_risk(self.websocket)
            response = response.replace("unprotected sexual intercourse", "sex")
            response = response.replace("STD", "STI")
            return response
        
        def search_provider_wrapper(zip_code: str) -> str:
            return search_provider(zip_code)

        async def assess_status_of_change_wrapper() -> str:
            return await assess_ttm_stage_single_question(self.websocket)
        
        async def record_support_request_wrapper() -> str:
            """Wrapper to handle the async record_support_request function"""
            return await record_support_request(self.websocket, self.chat_id)

                
        autogen.agentchat.register_function(
            record_support_request_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="record_support_request",
            description="""Do not immediately call this function. 
            Wait for the user to show signs of distress over time (DO NOT ACTIVATE THE FIRS TIME) or requests human support.
            First ask if they are sure they want human support. 
            If they do, then call this function. If they don't, then do not call this function.""",
        )

        autogen.agentchat.register_function(
            assess_status_of_change_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="assess_status_of_change",
            description="Assesses the status of change for the patient.",
        )


        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="answer_question",
            description="""Use this function to get HIV/PrEP information by passing the user's question as a parameter.
        Example: answer_question("What are the side effects of PrEP?")
        REQUIRED: Must be called before providing ANY HIV/PrEP information.""",
        )

        autogen.agentchat.register_function(
            assess_hiv_risk_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="assess_hiv_risk",
            description="Assesses HIV risk.",
        )

        autogen.agentchat.register_function(
            search_provider_wrapper,
            caller=counselor_assistant,
            executor=counselor,
            name="search_provider",
            description="Returns a list of nearby providers.",
        )

        speaker_transitions = {
            counselor: [counselor_assistant, counselor],
            counselor_assistant: [counselor, counselor_assistant],
            patient: []
        }


        
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
            max_round=12,
            allowed_or_disallowed_speaker_transitions=speaker_transitions,
            speaker_transitions_type="disallowed"
        )

        self.manager = TrackableGroupChatManager(
            groupchat=self.group_chat, 
            llm_config=self.config_list,
            system_message="""Ensure counselor is primary responder. It should ALWAYS use FAQ agent's 
            knowledge for information unless the information is not available. Only use assessment_bot and search_bot for 
            explicit requests.
            
                1. Only one agent should respond to each user message
                2. After an agent responds, wait for the user's next message
                3. Never have multiple agents respond to the same user message,
                4. Ensure counselor responds first using FAQ agent's knowledge, 
                unless explicitly asked for risk assessment or provider search


                
                """,
            websocket=self.websocket
        )

        # Adding Teachability
        teachability = Teachability(
            reset_db=False,
            path_to_db_dir="./tmp/interactive/teachability_db/{self.user_id}"
        )
        # Create a unique path and collection name for each user's teachability database
        user_db_path = os.path.join(
            "./tmp/interactive/teachability_db",
            f"user_{self.user_id}"
        )
        
        # Ensure the directory exists
        os.makedirs(user_db_path, exist_ok=True)

        # Initialize Teachability with user-specific path and collection name
        collection_name = f"memos_{self.user_id}"
        user_db_path = os.path.join(
            "./tmp/interactive/teachability_db",
            f"user_{self.user_id}"
        )

    
    # Initialize Teachability with thread-safe MemoStore
        teachability = Teachability(
            reset_db=False,
            path_to_db_dir=user_db_path,
            collection_name=collection_name,
            verbosity=0
        )
        teachability.add_to_agent(counselor)
        teachability.add_to_agent(counselor_assistant)


    def update_history(self, recipient, message, sender):
        self.agent_history.append({
            "sender": sender.name,
            "receiver": recipient.name,
            "message": message
        })
    
    def get_latest_response(self):
        """Get the latest valid response"""
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
        if not user_input:
            return
            
        try:
            self.update_history(self.agents[2], user_input, self.agents[2])
            await self.agents[1].a_initiate_chat(
                recipient=self.manager,
                message=user_input,
                websocket=self.websocket,
                clear_history=False,
                system_message="""Ensure counselor responds first using FAQ agent's knowledge, 
                unless explicitly asked for risk assessment or provider search.  Ensure only one agent responds per turn. """
            )
        except Exception as e:
            print(f"Chat error: {e}")
            raise

    def get_history(self):
        return self.agent_history   