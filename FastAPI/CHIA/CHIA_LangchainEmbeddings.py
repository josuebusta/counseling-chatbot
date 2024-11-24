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
    
        # OVERRIDING process_received_message from the autogen.groupchatmanager class
    def _process_received_message(self, message, sender, silent):
        # Send message to the WebSocket instead of printing
        
        if self.websocket:
            formatted_message = f"{sender.name}: {message}"
            asyncio.create_task(self.send_message(formatted_message))  # Send message to WebSocket
        return super()._process_received_message(message, sender, silent)

    async def send_message(self, message):
        # Ensure message is now in an accepted format (str, bytes, etc.)
        if isinstance(message, (str, bytes, bytearray, memoryview)):
            await self.websocket.send_text(message)  # Send via WebSocket
        else:
            raise TypeError(f"Unsupported message type: {type(message)}")
    


        


class HIVPrEPCounselor:
    async def initialize(self):
        await asyncio.sleep(1)

    def __init__(self, websocket: WebSocket):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.websocket = websocket
        print("websocket is!!", self.websocket)

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

        self.agent_history = []  # Track chat history here

        # Set up RAG components
        self.setup_rag()

        # Initialize agents
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

        counselor_system_message = """"You are an HIV PrEP counselor. Your goal 
        is to provide compassionate, thoughtful, and supportive responses based 
        on motivational interviewing guidelines. Whenever answering patient questions, 
        integrate relevant information from the RAG agent’s response if applicable, 
        but always personalize and adapt the information to ensure it feels warm, 
        empathetic, and conversational. Never respond with unfiltered output from 
        the tool—approach each conversation as a caring counselor.

        When handling casual greetings or general conversational questions, such 
        as 'How are you?' or 'Hi,' respond in a friendly, engaging manner, drawing 
        from your own knowledge rather than the RAG agent's input.

        If assessing HIV risk, follow a step-by-step approach, asking the questions 
        provided by the assessment tool one at a time. Use the patient’s responses 
        to assess their HIV risk sensitively and according to the tool’s guidelines, 
        being careful to reflect understanding and encouragement in every exchange. 
        After each function call, summarize and convey responses in conversational English, 
        ensuring each answer feels supportive and tailored to the individual.

        Above all, respond thoughtfully, always keeping the patient's emotional needs in mind."""
         
        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message=counselor_system_message,
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )




            # HIV assessment questions assistant to suggest the function to the assessment agent
        assessment_bot = autogen.AssistantAgent(
            name="assessment_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config= self.config_list,# configuration for autogen's enhanced inference API which is compatible with OpenAI API
            system_message="""When a patient asks to assess HIV risk, only suggest 
            the function you have been provided with. Ask each question from the 
            function one by one and return the final answer. Before executing the funcion, 
            make sure to:
            1. Tell the patients you will ask them a series of questions. 
            2. Use motivational interviewing guidelines when answering the question and be considerate and mindful of the patient's feelings.
            Once you have done that, suggest the function.
            Use the answer from the function to make a final answer.
            """,
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        search_bot = autogen.AssistantAgent(
            name="search_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            system_message="""Only when explicitly asked for a counselor or provider, 
            only suggest the function you have been provided with and use the ZIP code 
            provided as an argument. If no ZIP code has been provided, ask for the
            ZIP code. After getting the provider information, format it in a 
            conversational way, including:
            1. Use motivational interviewing guidelines when answering the question and be considerate and mindful of the patient's feelings.
            2. Clear organization of provider information
            3. Distance and available services
            4. Offer to answer questions about the providers
            5. Encourage reaching out to these providers""",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )

        status_bot = autogen.AssistantAgent(
            name="status_bot",
            is_termination_msg=lambda x: self.check_termination(x),
            llm_config=self.config_list,
            system_message="""Only when explicitly asked to assess status of change, 
            suggest the function that you have been provided with.""",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False}
        )






        FAQ_agent = autogen.AssistantAgent(
            name="suggests_retrieve_function",
            is_termination_msg=lambda x: self.check_termination(x),
            system_message="Suggests function to use to answer HIV/PrEP counselling questions. Answer with motivational interviewing guidelines in mind. Be considerate and mindful of the patient's feelings.",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        self.agents = [counselor, FAQ_agent, patient, assessment_bot, search_bot, status_bot]

        def answer_question_wrapper(user_question: str) -> str:
            return self.answer_question(user_question)
        
        async def assess_hiv_risk_wrapper() -> str:
            return await assess_hiv_risk(self.websocket)
        
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

        autogen.agentchat.register_function(
            assess_hiv_risk_wrapper,
            caller=assessment_bot,
            executor=counselor,
            name="assess_hiv_risk",
            description="Executes only when the user asks to ASSESS their HIV risk. Ask the questions with motivational interviewing guidelines in mind. Be considerate and mindful of the patient's feelings.",
        )

        autogen.agentchat.register_function(
            search_provider_wrapper,
            caller=search_bot,
            executor=counselor,
            name="search_provider",
            description="Returns a list of nearby providers.",
        )
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
        )

        self.manager = TrackableGroupChatManager(
            groupchat=self.group_chat, 
            llm_config=self.config_list,
            #websocket=None,  # Initialize websocket as None
            system_message="When asked a question about HIV/PREP, always call the FAQ agent before helping the counselor answer. When asked for a provider, always call the search bot agent befoere helping the counselor answer. In any case, the counselor should answer concisely and in conversational english. ",
            websocket=self.websocket
        )

        # Adding teachability to the counselor agent
        
        teachability = Teachability(
            reset_db=False,  # Use True to force-reset the memo DB, and False to use an existing DB.
            path_to_db_dir="./tmp/interactive/teachability_db"  # Can be any path, but teachable agents in a group chat require unique paths.
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
            return self.group_chat.messages[-1]["content"]  # Retrieves the most recent message
        return "No messages found."  # Fallback if no messages are available


    async def initiate_chat(self, user_input: str):
        self.update_history(self.agents[2], user_input, self.agents[2])  # Patient is the third agent
        await self.agents[2].a_initiate_chat(
            recipient=self.manager,
            message=user_input,
            websocket=self.websocket,
            system_message="If you are unsure whose turn it is to talk, you should let the counselor respond. Make sure the final answer makes sense given the question asked. For conversational questions like - How are you? or Hi-, respond in a friendly and engaging manner and DO NOT use the RAG response. When the patient specifically asks to assess their HIV risk, use the function suggested for that purpose. When the patient asks for their nearest provider, use the function suggested for that purpose. When asked any other question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information."
        )

    
   

    def get_history(self):
        return self.agent_history

