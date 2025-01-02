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
from .functions import assess_hiv_risk, search_provider, assess_ttm_stage_single_question


# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class TrackableGroupChatManager(autogen.GroupChatManager):
    def _process_received_message(self, message, sender, silent):
        if self.websocket:
            formatted_message = f"{sender.name}: {message}"
            asyncio.create_task(self.send_message(formatted_message))
        return super()._process_received_message(message, sender, silent)

    async def send_message(self, message):
        if isinstance(message, (str, bytes, bytearray, memoryview)):
            await self.websocket.send_text(message)
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")

class HIVPrEPCounselor:
    async def initialize(self):
        await asyncio.sleep(1)

    def __init__(self, websocket: WebSocket, user_id: str):
        print("user_id", user_id)
        load_dotenv()
        self.user_id = user_id
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.websocket = websocket
        print("websocket is!!", self.websocket)
        self.websocket.send_text("Hello, world!")

        if not self.api_key:
            raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

        self.config_list = {
            "model": "gpt-4o-mini",
            "api_key": self.api_key
        }

        self.llm_config_counselor = {
            "temperature": 0,
            "timeout": 300,
            "cache_seed": 43,
            "config_list": self.config_list,
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
       
        patient = autogen.UserProxyAgent(
            name="patient",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=10,
            code_execution_config={"work_dir": "coding", "use_docker": False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        
        counselor_system_message = """You are CHIA, an HIV PrEP counselor. 
        After the user says hi, respond (make sure to take into account if you already have their name):
        Hello, my name is CHIA. It's nice to meet you. What's your name? (Doesn't have to be your real name)

        When the user has provided their name:
        1. Explaining that everything is confidential and you won't judge
        2. Use this formulation: 
        - “Thank you for taking the time today to chat.
        Everything you say is completely confidential and since I'm an AI, I'm 
        really not going to judge anything you say. My goal is to make sure you 
        have accurate and up to date information to be the healthiest version of you!”
        - “Let me start off by asking you a couple questions if you don’t mind. Your answers will
        help me provide you the most accurate information possible. Then, you can ask me
        anything you want!”
        - “First, tell me a little about yourself. Do you identify as a man or woman or another
        gender?”

        When providing information:
        - Replace "unprotected sex" with "sex" or "condomless sex"
        - Use "STI" instead of "STD"
        - Be warm, empathetic, and conversational
        - If there's a pause, ask "Do you mind if I ask you some more questions?"
        
        Provide compassionate, thoughtful responses using motivational interviewing guidelines. 
        When answering questions, personalize the information to ensure it feels warm and conversational.
        Never give unfiltered responses - always approach as a caring counselor.

        For risk assessment:
        - Ask questions one at a time
        - Use updated terminology
        - Be sensitive and supportive
        - Reflect understanding in every exchange

        Above all, respond thoughtfully, keeping the patient's emotional needs in mind."""

        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message=counselor_system_message,
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        assessment_bot_system_message = """You are a knowledgeable and empathetic HIV counselor. Your ONLY role is to help assess HIV risk and provide guidance about PrEP when EXPLICITLY asked by the user. 

        YOU SHOULD ONLY RESPOND WHEN ONE OF THESE PHRASES IS USED:
        - "assess my risk"
        - "check my risk"
        - "what's my risk"
        - "am I at risk"
        - "risk assessment"
        - Or similar EXPLICIT requests for risk assessment

        DO NOT activate for:
        - General questions about sexual activity 
        - General questions about HIV/PrEP
        - Status updates or check-ins
        - Standard medical history questions
        - Let the counselor handle those conversations

        WHEN AND ONLY WHEN explicitly asked to assess risk:

        1. Start with:
        "I'll help assess your HIV risk factors. This is confidential, and we'll go through several questions step by step. Share at your comfort level."

        2. Ask these questions ONE AT A TIME:
        - "Have you had sex without protection in the past 3 months?"
        - "Have you had multiple sexual partners in the past 12 months?"
        - "Have you used intravenous drugs or shared needles?"
        - "Do you have a sexual partner who is HIV positive or whose HIV status you don't know?"
        - "Have you been diagnosed with any STIs in the past 12 months?"

        3. After the assessment is complete:
        If high risk indicated:
        - "Based on your responses, you may benefit from PrEP. This is just an initial assessment - I recommend discussing this with a healthcare provider."
        
        If low risk indicated:
        - "Based on your responses, you're currently at lower risk. Continue your safer practices and consider regular testing."

        IMPORTANT: Only respond when explicitly asked for risk assessment. Otherwise, stay silent and let the counselor handle the conversation."""

        assessment_bot = autogen.AssistantAgent(
            name="assessment_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            system_message=assessment_bot_system_message,
            
            # """
            # ONLY execute when the user asks to assess their HIV risk.
            # When assessing HIV risk:
            # 1. First explain: "I'll need to ask you a few questions to better understand your situation. 
            #    Everything you share is confidential, and I'm here to help without judgment."
            # 2. Ask questions one at a time using updated terminology:
            #    - Use "sex" instead of "unprotected sexual intercourse"
            #    - Use "STI" instead of "STD"
            # 3. Be supportive and considerate throughout
            # 4. Provide clear next steps based on the assessment""",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        search_bot = autogen.AssistantAgent(
            name="search_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            system_message="""Only when explicitly asked for a counselor or provider, 
            suggest the function with the ZIP code provided. If no ZIP code given, ask for it.
            Format provider information conversationally, including:
            1. Clear organization of information
            2. Distance and services
            3. Offer to answer questions
            4. Encourage reaching out
            Use motivational interviewing and be considerate of feelings.""",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        status_bot = autogen.AssistantAgent(
            name="status_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            system_message="Only suggest the status assessment function when explicitly asked.",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        FAQ_agent = autogen.AssistantAgent(
            name="suggests_retrieve_function",
            is_termination_msg=lambda x: self.check_termination(x),
            system_message="Suggests function for HIV/PrEP questions. Use motivational interviewing and be mindful of feelings.",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        self.agents = [counselor, FAQ_agent, patient, assessment_bot, search_bot, status_bot]

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

        autogen.agentchat.register_function(
            assess_status_of_change_wrapper,
            caller=status_bot,
            executor=counselor,
            name="assess_status_of_change",
            description="Assesses the status of change for the patient.",
        )

        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=FAQ_agent,
            executor=counselor,
            name="answer_question",
            description="Retrieves embedding data content to answer user's question.",
        )

        # autogen.agentchat.register_function(
        #     assess_hiv_risk_wrapper,
        #     caller=assessment_bot,
        #     executor=counselor,
        #     name="assess_hiv_risk",
        #     description="Executes HIV risk assessment using updated terminology and motivational interviewing.",
        # )

        autogen.agentchat.register_function(
            search_provider_wrapper,
            caller=search_bot,
            executor=counselor,
            name="search_provider",
            description="Returns a list of nearby providers.",
        )
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[]

        )

        self.manager = TrackableGroupChatManager(
            groupchat=self.group_chat, 
            llm_config=self.config_list,
            system_message="""Guide conversations naturally through PrEP topics. 
            Have CHIA respond conversationally and maintain flow. 
            Start with proper introduction and use updated terminology.
            If there's a pause, prompt with follow-up questions.""",
            websocket=self.websocket
        )
        

        # teachability = Teachability(
        #     reset_db=False,
        #     path_to_db_dir="./tmp/interactive/teachability_db/{self.user_id}"
        # )
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

    def update_history(self, recipient, message, sender):
        self.agent_history.append({
            "sender": sender.name,
            "receiver": recipient.name,
            "message": message
        })
    
    def get_latest_response(self):
        if self.group_chat.messages:
            return self.group_chat.messages[-1]["content"]
        return "No messages found."

    # async def initiate_chat(self, user_input: str):
    #     self.update_history(self.agents[2], user_input, self.agents[2])
    #     await self.agents[2].a_initiate_chat(
    #         recipient=self.manager,
    #         message=user_input,
    #         websocket=self.websocket,
    #         system_message="""Guide natural conversation flow, letting CHIA lead when unsure.
    #         For HIV/PrEP questions, consult FAQ agent then have CHIA respond conversationally.
    #         For casual greetings, respond warmly without using RAG.
    #         For HIV risk assessment, use the assessment function.
    #         For provider searches, use the provider function.
    #         Always use updated terminology (sex instead of unprotected sex, STI instead of STD).""",
    #     )
    async def initiate_chat(self, user_input: str = None):
        # if not self.group_chat.messages:  # If this is the first message
        #     # initial_message = "Hello, my name is CHIA. It's nice to meet you. What's your name? (Doesn't have to be your real name)"
            
        #     # # First send directly to websocket for immediate display
        #     # if self.websocket:
        #     #     await self.websocket.send_text(f"CHIA: {initial_message}")
            
        #     # Then properly initiate the chat through the manager
        #     await self.manager.a_initiate_chat(
        #         recipient=self.agents[2],  # patient
        #         message="hey!!",
        #         websocket=self.websocket
        #     )
        # else:
        # Handle subsequent messages
        self.update_history(self.agents[2], user_input, self.agents[2])
        await self.agents[2].a_initiate_chat(
            recipient=self.manager,
            message=user_input,
            websocket=self.websocket,
            system_message="""Guide natural conversation flow...""",
        )

    def get_history(self):
        return self.agent_history