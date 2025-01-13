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
from .functions import search_provider, assess_ttm_stage_single_question, assess_hiv_risk

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

    def _process_received_message(self, message, sender, silent):
        if self.websocket:
            formatted_message = self._format_message(message, sender)
            if formatted_message and formatted_message not in self._message_history:  
                asyncio.create_task(self.send_message(formatted_message))
                self._message_history.add(formatted_message)
        return super()._process_received_message(message, sender, silent)

    def _format_message(self, message, sender) -> str:
        """Format the message for display, handling various message types"""
        try:
            # Skip function calls and empty messages
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
        prefixes = ["counselor:", "CHIA:", "assessment_bot:", "patient:"]
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
    def __init__(self, websocket: WebSocket, user_id: str):
        load_dotenv()
        self.user_id = user_id
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.websocket = websocket

        if not self.api_key:
            raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

        self.config_list = {
            "model": "gpt-4o-mini",
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
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        retriever = vectorstore.as_retriever()
        self.qa_chain = RetrievalQA.from_chain_type(
            llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
        )

    def answer_question(self, question: str) -> str:
        self.result = self.qa_chain.invoke({"query": question})
        return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

    def initialize_agents(self):
        counselor_system_message = """You are CHIA, the primary HIV PrEP counselor. You are the main responder
        for all conversations and should use the FAQ agent's knowledge to provide accurate information.

        Key Guidelines:
        1. YOU ARE THE PRIMARY RESPONDER. Always respond first unless:
           - User explicitly asks for risk assessment
           - User explicitly asks to find a provider
        
        2. For HIV/PrEP questions:
           - Use the FAQ agent's knowledge base through the answer_question function
           - Keep responses warm and conversational
           - Use "sex without condoms" instead of "unprotected sex"
           - Use "STI" instead of "STD"
        
        3. When user shares their name:
           - Thank them for chatting
           - Explain confidentiality
           - Ask about gender identity
        
        4. Let specialized tools handle ONLY:
           - HIV risk assessment (when explicitly requested)
           - Provider search (when explicitly requested)

        5. I someone thinks they have hiv, answer in the way you usually would but also make sure to tell them you are able to assess their risk or search for providers.
        
        Always respond thoughtfully and personally, using the FAQ agent's knowledge
        when answering questions about HIV/PrEP."""

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

        FAQ_agent = autogen.AssistantAgent(
            name="FAQ_agent",
            system_message="""You provide HIV/PrEP information through the answer_question function.
            You support the counselor by providing accurate information from the knowledge base.""",
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list
        )

        assessment_bot = autogen.AssistantAgent(
            name="assessment_bot",
            system_message="""ONLY respond when you see EXACT phrases like:
            - "assess my risk"
            - "check my risk"
            - "what's my risk"
            - "am I at risk"

            When activated, ALWAYS follow this exact sequence:
                1. First provide this introduction that makes sense given the context:
                "I'll help assess your HIV risk factors. This will involve a few questions about your sexual health and activities. 
                Everything you share is completely confidential, and I'm here to help without judgment. Let's go through this step by step."
                
                2. THEN use the assess_hiv_risk function to ask the questions.
            
            ANY OTHER QUERIES should be handled by the counselor.
            When activated, use ONLY the assess_hiv_risk function.""",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        search_bot = autogen.AssistantAgent(
            name="search_bot",
            system_message="""ONLY respond when user EXPLICITLY asks to:
            - Find a provider
            - Locate a clinic
            - Get testing locations
            
            ANY OTHER QUERIES should be handled by the counselor.
            When activated, use the search_provider function.""",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        self.agents = [counselor, FAQ_agent, patient, assessment_bot, search_bot]

        def answer_question_wrapper(user_question: str) -> str:
            return self.answer_question(user_question)
        
        async def assess_hiv_risk_wrapper() -> str:
            response = await assess_hiv_risk(self.websocket)
            response = response.replace("unprotected sexual intercourse", "sex")
            response = response.replace("STD", "STI")
            return response
        
        def search_provider_wrapper(zip_code: str) -> str:
            return search_provider(zip_code)

        # Register functions
        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=FAQ_agent,
            executor=counselor,
            name="answer_question",
            description="Retrieves HIV/PrEP information from the knowledge base.",
        )

        autogen.agentchat.register_function(
            assess_hiv_risk_wrapper,
            caller=assessment_bot,
            executor=counselor,
            name="assess_hiv_risk",
            description="Assesses HIV risk.",
        )

        autogen.agentchat.register_function(
            search_provider_wrapper,
            caller=search_bot,
            executor=counselor,
            name="search_provider",
            description="Returns a list of nearby providers.",
        )
        speaker_transitions = {
        # Counselor can respond to patient queries
        counselor: [patient],
        # Assessment bot can only respond to patient when risk assessment is requested
        assessment_bot: [patient],
        # FAQ agent shouldn't respond directly
        FAQ_agent: [patient, counselor],
        # Search bot can only respond to patient when provider search is requested
        search_bot: [patient],
        # Patient can receive responses from any agent
        patient: [counselor, assessment_bot, search_bot]
    }
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
            max_round=12,
            allowed_or_disallowed_speaker_transitions=speaker_transitions,
            speaker_transitions_type="allowed"
        )

        self.manager = TrackableGroupChatManager(
            groupchat=self.group_chat, 
            llm_config=self.config_list,
            system_message="""Ensure counselor is primary responder, using FAQ agent's 
            knowledge for information. Only use assessment_bot and search_bot for 
            explicit requests.
            
            ONE RESPONSE PER USER MESSAGE:
                1. Only one agent should respond to each user message
                2. After an agent responds, wait for the user's next message
                3. Never have multiple agents respond to the same user message,
                4. Ensure counselor responds first using FAQ agent's knowledge, 
                unless explicitly asked for risk assessment or provider search.""",
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

        teachability.add_to_agent(assessment_bot)

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
            await self.agents[2].a_initiate_chat(
                recipient=self.manager,
                message=user_input,
                websocket=self.websocket,
            

                clear_history=False,
                max_consecutive_auto_reply=1
            )
        except Exception as e:
            print(f"Chat error: {e}")
            raise

    def get_history(self):
        return self.agent_history   