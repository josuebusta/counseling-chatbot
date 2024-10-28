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
        return x.get("content", "").rstrip().endswith("TERMINATE")

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

        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message="You are an HIV PrEP counselor. Be considerate. Call the function provided to answer user's questions. NEVER stop speaking before you have used the result from the function call, and transformed into conversational english to answer the question.",
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        FAQ_agent = autogen.AssistantAgent(
            name="suggests_retrieve_function",
            is_termination_msg=lambda x: self.check_termination(x),
            system_message="Suggests function to use to answer HIV/PrEP counselling questions",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list,
            websocket=self.websocket
        )

        self.agents = [counselor, FAQ_agent, patient]

        def answer_question_wrapper(user_question: str):
            return self.answer_question(user_question)
        
        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=FAQ_agent,
            executor=counselor,
            name="answer_question",
            description="Retrieves embedding data content to answer user's question.",
        )
        
        self.group_chat = autogen.GroupChat(
            agents=self.agents,
            messages=[],
        )

        self.manager = TrackableGroupChatManager(
            groupchat=self.group_chat, 
            llm_config=self.config_list,
            #websocket=None,  # Initialize websocket as None
            system_message="When asked a question about HIV/PREP, always call the FAQ agent before helping the counselor answer. Then have the counselor answer concisely.",
            websocket=self.websocket
        )

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
            websocket=self.websocket
        )

    def get_history(self):
        return self.agent_history