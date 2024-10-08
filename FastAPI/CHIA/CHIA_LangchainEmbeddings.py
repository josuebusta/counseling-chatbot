import os
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain import hub
import autogen
import asyncio

# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class WorkflowManager:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')

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

        self.agent_history = []  # To track conversation history

        # Set up RAG components
        self.setup_rag()

        # Initialize agents
        self.initialize_agents()

    def check_termination(self, x):
        print(f"Message content: {x}")
        return x.get("content", "").rstrip().endswith("TERMINATE")

    def setup_rag(self):
        prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")
        loader = WebBaseLoader("https://github.com/amarisg25/counselling-chatbot/blob/main/embeddings/HIV_PrEP_knowledge_embedding.json")
        data = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_splits = text_splitter.split_documents(data)
        print(f"Number of splits: {len(all_splits)}")

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
            llm_config=self.config_list
        )

        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions.",
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list
        )

        FAQ_agent = autogen.AssistantAgent(
            name="suggests_retrieve_function",
            is_termination_msg=lambda x: self.check_termination(x),
            system_message="Suggests function to use to answer HIV/PrEP counseling questions",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list
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

        group_chat = autogen.GroupChat(
            agents=self.agents, 
            messages=[], 
        )

        self.manager = autogen.GroupChatManager(
            groupchat=group_chat, 
            llm_config=self.config_list, 
            system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information."
        )

        # manager.initiate_chat(
        #     patient,
        #     message="How can I help you?",
        # )

        def update_history(recipient, message, sender, config):
            self.agent_history.append({"sender": sender.name, "receiver": recipient.name, "message": message})

        for agent in self.agents:
            agent.register_reply(
                [autogen.Agent, None],
                reply_func=update_history, 
                config={"callback": None},
            )

    async def get_response(self, user_message: str) -> str:
        # Here you can implement asynchronous handling if necessary
        response = self.answer_question(user_message)
        self.agent_history.append({"sender": "patient", "receiver": "counselor", "message": user_message})
        self.agent_history.append({"sender": "counselor", "receiver": "patient", "message": response})
        return response

    def get_history(self):
        return self.agent_history

    def run(self):
        # Placeholder for any synchronous run logic if needed
        pass

    async def handle_message(self, message: str) -> str:
        # Use AutoGen to generate the response
        response_message = await self.manager.answer_question(message)
        return response_message

if __name__ == "__main__":
    manager = WorkflowManager()
    manager.run()



# import os
# from dotenv import load_dotenv
# import json
# from langchain_community.document_loaders import DirectoryLoader, JSONLoader, WebBaseLoader
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.vectorstores import Chroma
# from langchain_openai import ChatOpenAI
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.chains import RetrievalQA
# from langchain import hub
# import autogen
# import asyncio

# # CONFIGURATION 
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

# class HIVPrEPCounselor:
#     async def initialize(self):
#         # Perform asynchronous initialization here
#         await asyncio.sleep(1)
        
#     def __init__(self):
# # Load environment variables from .env file
#         load_dotenv()
#         self.api_key = os.getenv('OPENAI_API_KEY')

#         if not self.api_key:
#             raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

#         self.config_list = {
#             "model": "gpt-4o-mini", 
#             "api_key": self.api_key  # Directly use the api_key variable
#         }

#         # Function description
#         self.llm_config_counselor = {
#             "temperature": 0,
#             "timeout": 300,
#             "cache_seed": 43,
#             "config_list": self.config_list,
#         }

#         # Set up RAG components
#         self.setup_rag()

#         # Initialize agents
#         self.initialize_agents()


#         # FUNCTION TO CHECK TERMINATION
#         # Search provider user proxy agent (Debugging purposes)
#     def check_termination(self, x):
#         """
#         Checks if the message content ends with "TERMINATE" to determine if the conversation should end.

#         Parameters:
#         x (dict): A dictionary containing the message content

#         Returns:
#         bool: True if the message ends with "TERMINATE", False otherwise
#         """

#         print(f"Message content: {x}")
#         return x.get("content", "").rstrip().endswith("TERMINATE")


#     def setup_rag(self):
#         # RAG prompt
#         # Load the latest version of the prompt
#         prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

#         # Load documents from a URL
#         # loader = JSONLoader('embeddings/HIV_PrEP_knowledge_embedding.json', jq_schema='.quiz', text_content=False)
#         loader = WebBaseLoader("https://github.com/amarisg25/counselling-chatbot/blob/main/embeddings/HIV_PrEP_knowledge_embedding.json")
#         data = loader.load()

#         # Split documents into manageable chunks
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
#         all_splits = text_splitter.split_documents(data)
#         print(f"Number of splits: {len(all_splits)}")
#         # Check the contents of all_splits
#         # for i, split in enumerate(all_splits):
#         #     print(f"Split Document {i}: {split}")

#         # Store splits in the vector store
#         vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(openai_api_key=self.api_key))

#         # Initialize the LLM with the correct model
#         llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

 
#         # Initialize RetrievalQA
#         retriever = vectorstore.as_retriever()
#         self.qa_chain = RetrievalQA.from_chain_type(
#             llm, retriever= retriever, chain_type_kwargs={"prompt": prompt}
#         )

#     def answer_question(self, question: str) -> str:
#         """
#         Answer a question based on HIV PrEP knowledge base.

#         :param question: The question to answer.
#         :return: The answer as a string.
#         """
#         self.result = self.qa_chain.invoke({"query": question})
#         return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

    
#     def initialize_agents(self):
#         # AGENTS INITALIZATION
#         # Patient (Chatbot-user)
#         patient = autogen.UserProxyAgent(
#             name="patient",
#             human_input_mode="ALWAYS",
#             max_consecutive_auto_reply=10,
#             code_execution_config={"work_dir": "coding", "use_docker": False},
#             llm_config=self.config_list
#         )


#         # Main counselor - answers general questions 
#         counselor = autogen.UserProxyAgent(
#             name="counselor",
#             system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions. ",
#             is_termination_msg=lambda x: self.check_termination(x),
#             human_input_mode="NEVER",
#             code_execution_config={"work_dir":"coding", "use_docker":False},
#             llm_config=self.config_list
#         )

#         # counselor_aid - gives the counselor some context
#         FAQ_agent = autogen.AssistantAgent(
#             name="suggests_retrieve_function",
#             is_termination_msg=lambda x: self.check_termination(x),
#             system_message="Suggests function to use to answer HIV/PrEPcounselling questions",
#             human_input_mode="NEVER",
#             code_execution_config={"work_dir":"coding", "use_docker":False},
#             llm_config=self.config_list
#         )

#         self.agents = [counselor, FAQ_agent, patient]
        

#         # Define the wrapper function
#         def answer_question_wrapper(user_question: str):
#             return self.answer_question(user_question)
        
#         # Register the wrapper function with autogen
#         autogen.agentchat.register_function(
#             answer_question_wrapper,
#             caller=FAQ_agent,
#             executor=counselor,
#             name="answer_question",
#             description="Retrieves embedding data content to answer user's question.",
#         )

#         #INITIALIZE THE GROUP CHAT

#         group_chat = autogen.GroupChat(
#             agents= self.agents, 
#             messages=[], 
#             )

#         manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.config_list, system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information.")

#         manager.initiate_chat(
#             patient,
#             message="How can I help you?",
#         )

#         def update_history(recipient, message, sender, config):
#             self.agent_history.append({"sender": sender.name, "receiver": recipient.name, "message": message})

#         for agent in self.agents:
#             agent.register_reply(
#                 [autogen.Agent, None],
#                 reply_func=update_history, 
#                 config={"callback": None},
#             )



# if __name__ == "__main__":
#     counselor = HIVPrEPCounselor()
#     counselor.run()

# # # # # async def handle_user_message(self, user_message: str) -> str:
# # # # #     """Handle the user message and return the response."""
# # # # #     # Call the appropriate functions here
# # # # #     return self.answer_question(user_message)

# # # # # import os
# # # # # from dotenv import load_dotenv
# # # # # from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# # # # # import autogen
# # # # # import asyncio

# # # # # # Load environment variables
# # # # # load_dotenv()
# # # # # api_key = os.getenv('OPENAI_API_KEY')

# # # # # if not api_key:
# # # # #     raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

# # # # # class HIVPrEPCounselor:
# # # # #     def __init__(self):
# # # # #         self.api_key = api_key
# # # # #         self.config_list = {
# # # # #             "model": "gpt-4o-mini", 
# # # # #             "api_key": self.api_key
# # # # #         }
# # # # #         self.agents = []
# # # # #         self.group_chat_manager = None

# # # # #     async def setup_agents(self):
# # # # #         # Set up the agents for group chat
# # # # #         patient = autogen.UserProxyAgent(
# # # # #             name="patient",
# # # # #             human_input_mode="ALWAYS",
# # # # #             max_consecutive_auto_reply=10,
# # # # #             llm_config=self.config_list,
# # # # #             code_execution_config={"work_dir":"coding", "use_docker":False},
# # # # #         )

# # # # #         counselor = autogen.UserProxyAgent(
# # # # #             name="counselor",
# # # # #             system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions.",
# # # # #             is_termination_msg=lambda x: self.check_termination(x),
# # # # #             human_input_mode="NEVER",
# # # # #             llm_config=self.config_list,
# # # # #             code_execution_config={"work_dir":"coding", "use_docker":False},
# # # # #         )

# # # # #         FAQ_agent = autogen.AssistantAgent(
# # # # #             name="FAQ_agent",
# # # # #             system_message="You assist with retrieving information on HIV/PrEP.",
# # # # #             human_input_mode="NEVER",
# # # # #             llm_config=self.config_list
# # # # #         )

# # # # #         self.agents = [patient, counselor, FAQ_agent]

# # # # #         # Set up GroupChat manager
# # # # #         self.group_chat_manager = autogen.GroupChatManager(
# # # # #             groupchat=autogen.GroupChat(agents=self.agents, messages=[]),
# # # # #             llm_config=self.config_list,
# # # # #             system_message="When asked a question about HIV/PREP, call the FAQ agent before having the counselor answer."
# # # # #         )

# # # # #     async def handle_user_message(self, user_message: str):
# # # # #         """Send the user message to the group chat and get responses."""
# # # # #         if not self.group_chat_manager:
# # # # #             await self.setup_agents()

# # # # #         # Patient sends the message
# # # # #         patient = self.agents[0]
        
# # # # #         # The manager initiates the conversation with a greeting if it's the first message
# # # # #         if len(self.group_chat_manager.groupchat.messages) == 0:
# # # # #             await self.group_chat_manager.initiate_chat(patient, message="Hi, how can I help you?")
        
# # # # #         # Continue the conversation with the user's message
# # # # #         await self.group_chat_manager.initiate_chat(patient, message=user_message)

# # # # #         # Collect responses from the agents
# # # # #         messages = [agent.history[-1]["message"] for agent in self.agents]
# # # # #         return "\n".join(messages)

# # # class HIVPrEPCounselor:
# # #     """
# # #     HIVPrEPCounselor integrates with AutoGenChatManager to handle chat interactions
# # #     for HIV PrEP counseling.
# # #     """

# # #     def __init__(self):
# # #         # Load environment variables from .env file
# # #         load_dotenv()
# # #         self.api_key = os.getenv('OPENAI_API_KEY')

# # #         if not self.api_key:
# # #             raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

# # #         self.config_list = {
# # #             "model": "gpt-4o-mini",
# # #             "api_key": self.api_key  # Directly use the api_key variable
# # #         }

# # #         # Function description
# # #         self.llm_config_counselor = {
# # #             "temperature": 0,
# # #             "timeout": 300,
# # #             "cache_seed": 43,
# # #             "config_list": self.config_list,
# # #         }

# # #         # Initialize components
# # #         self.message_queue = Queue()
# # #         self.websocket_manager = WebSocketConnectionManager()

# # #         # Initialize RAG components
# # #         self.setup_rag()

# # #         # Initialize agents
# # #         self.initialize_agents()

# # #     def check_termination(self, x: Dict[str, Any]) -> bool:
# # #         """
# # #         Checks if the message content ends with "TERMINATE" to determine if the conversation should end.

# # #         Parameters:
# # #         x (dict): A dictionary containing the message content

# # #         Returns:
# # #         bool: True if the message ends with "TERMINATE", False otherwise
# # #         """
# # #         return x.get("content", "").rstrip().endswith("TERMINATE")

# # #     def setup_rag(self):
# # #         # RAG prompt
# # #         prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

# # #         # Load documents from a URL
# # #         loader = WebBaseLoader("https://raw.githubusercontent.com/amarisg25/counselling-chatbot/main/embeddings/HIV_PrEP_knowledge_embedding.json")
# # #         data = loader.load()

# # #         # Split documents into manageable chunks
# # #         text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
# # #         all_splits = text_splitter.split_documents(data)
       
# # #         # Store splits in the vector store
# # #         vectorstore = Chroma.from_documents(
# # #             documents=all_splits,
# # #             embedding=OpenAIEmbeddings(openai_api_key=self.api_key)
# # #         )

# # #         # Initialize the LLM with the correct model
# # #         llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# # #         # Initialize RetrievalQA
# # #         retriever = vectorstore.as_retriever()
# # #         self.qa_chain = RetrievalQA.from_chain_type(
# # #             llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
# # #         )

# # #     def answer_question(self, question: str) -> str:
# # #         """
# # #         Answer a question based on HIV PrEP knowledge base.

# # #         :param question: The question to answer.
# # #         :return: The answer as a string.
# # #         """
    
# # #         self.result = self.qa_chain.invoke({"query": question})
# # #         return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

# # #     def initialize_agents(self):
# # #         # Initialize agents
# # #         patient = autogen.UserProxyAgent(
# # #             name="patient",
# # #             human_input_mode="ALWAYS",
# # #             max_consecutive_auto_reply=10,
# # #             code_execution_config={"work_dir": "coding", "use_docker": False},
# # #             llm_config=self.config_list
# # #         )

# # #         counselor = autogen.UserProxyAgent(
# # #             name="counselor",
# # #             system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions.",
# # #             is_termination_msg=lambda x: self.check_termination(x),
# # #             human_input_mode="NEVER",
# # #             code_execution_config={"work_dir": "coding", "use_docker": False},
# # #             llm_config=self.config_list
# # #         )

# # #         FAQ_agent = autogen.AssistantAgent(
# # #             name="suggests_retrieve_function",
# # #             is_termination_msg=lambda x: self.check_termination(x),
# # #             system_message="Suggests function to use to answer HIV/PrEP counselling questions",
# # #             human_input_mode="NEVER",
# # #             code_execution_config={"work_dir": "coding", "use_docker": False},
# # #             llm_config=self.config_list
# # #         )

# # #         self.agents = [counselor, FAQ_agent, patient]

# # #         # Define the wrapper function
# # #         def answer_question_wrapper(user_question: str):
# # #             return self.answer_question(user_question)

# # #         # Register the wrapper function with autogen
# # #         autogen.agentchat.register_function(
# # #             answer_question_wrapper,
# # #             caller=FAQ_agent,
# # #             executor=counselor,
# # #             name="answer_question",
# # #             description="Retrieves embedding data content to answer user's question.",
# # #         )

# # #         # Initialize the GroupChat
# # #         group_chat = autogen.GroupChat(
# # #             agents=self.agents,
# # #             messages=[],
# # #         )

# # #         # Initialize the AutoGen GroupChatManager
# # #         self.group_chat_manager = autogen.GroupChatManager(
# # #             groupchat=group_chat,
# # #             llm_config=self.config_list,
# # #             system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information."
# # #         )

# # #         self.group_chat_manager.initiate_chat(
# # #             patient,
# # #             message="How can I help you?",
# # #         )

# # #         def update_history(recipient, message, sender, config):
# # #             # You can implement history updating logic her
# # #             for agent in self.agents:
# # #                 agent.register_reply(
# # #                     [autogen.Agent, None],
# # #                     reply_func=update_history,
# # #                     config={"callback": None},
# # #                 )

# # #     async def handle_user_message(self, user_message: str, connection_id: str) -> str:
# # #         """
# # #         Handle the user message and return the response.

# # #         :param user_message: The message from the user.
# # #         :param connection_id: The unique identifier for the WebSocket connection.
# # #         :return: The response from the counselor.
# # #         """
# # #         # Create a Message instance

# # #         # Define history (can be fetched from a database or in-memory store)
# # #         history: List[Dict[str, Any]] = []

# # #         # Process the message using AutoGenChatManager
# # #         response_message = self.websocket_manager.chat(
# # #             message=user_message,
# # #             history=history,
# # #             workflow=None,  # Define or load your workflow configuration
# # #             connection_id=connection_id,
# # #             user_dir="user_data"  # Define the user directory
# # #         )

# # #         print(f"Generated response: {response_message.content}")

# # #         return response_message.content

# # # CHIA/CHIA_LangchainEmbeddings.py

# # import os
# # from dotenv import load_dotenv
# # from langchain_community.document_loaders import WebBaseLoader
# # from langchain_openai import OpenAIEmbeddings, ChatOpenAI
# # from langchain_community.vectorstores import Chroma
# # from langchain.text_splitter import RecursiveCharacterTextSplitter
# # from langchain.chains import RetrievalQA
# # from langchain import hub
# # import autogen
# # from queue import Queue
# # from typing import Any, Dict, List
# # import asyncio
# # from websocket_connection_manager import WebSocketConnectionManager

# # class HIVPrEPCounselor:
# #     """
# #     HIVPrEPCounselor integrates with AutoGenChatManager to handle chat interactions
# #     for HIV PrEP counseling.
# #     """

# #     def __init__(self):
# #         # Load environment variables from .env file
# #         load_dotenv()
# #         self.api_key = os.getenv('OPENAI_API_KEY')

# #         if not self.api_key:
# #             raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

# #         self.config_list = {
# #             "model": "gpt-4o-mini",
# #             "api_key": self.api_key  # Directly use the api_key variable
# #         }

# #         # Function description
# #         self.llm_config_counselor = {
# #             "temperature": 0,
# #             "timeout": 300,
# #             "cache_seed": 43,
# #             "config_list": self.config_list,
# #         }

# #         # Initialize components
# #         self.message_queue = asyncio.Queue()
# #         self.websocket_manager = WebSocketConnectionManager()

# #         # Initialize RAG components
# #         self.setup_rag()

# #         # Initialize agents
# #         self.initialize_agents()

# #     def check_termination(self, x: Dict[str, Any]) -> bool:
# #         """
# #         Checks if the message content ends with "TERMINATE" to determine if the conversation should end.
# #         """
# #         return x.get("content", "").rstrip().endswith("TERMINATE")

# #     def setup_rag(self):
# #         # RAG prompt
# #         prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

# #         # Load documents from a URL
# #         loader = WebBaseLoader("https://raw.githubusercontent.com/amarisg25/counselling-chatbot/main/embeddings/HIV_PrEP_knowledge_embedding.json")
# #         data = loader.load()

# #         # Split documents into manageable chunks
# #         text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
# #         all_splits = text_splitter.split_documents(data)
       
# #         # Store splits in the vector store
# #         vectorstore = Chroma.from_documents(
# #             documents=all_splits,
# #             embedding=OpenAIEmbeddings(openai_api_key=self.api_key)
# #         )

# #         # Initialize the LLM with the correct model
# #         llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# #         # Initialize RetrievalQA
# #         retriever = vectorstore.as_retriever()
# #         self.qa_chain = RetrievalQA.from_chain_type(
# #             llm, retriever=retriever, chain_type_kwargs={"prompt": prompt}
# #         )

# #     async def answer_question(self, question: str) -> str:
# #         """
# #         Answer a question based on HIV PrEP knowledge base.
# #         """
# #         self.result = self.qa_chain.invoke({"query": question})
# #         return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

# #     def initialize_agents(self):
# #         # Initialize agents
# #         patient = autogen.UserProxyAgent(
# #             name="patient",
# #             human_input_mode="ALWAYS",
# #             max_consecutive_auto_reply=10,
# #             code_execution_config={"work_dir": "coding", "use_docker": False},
# #             llm_config=self.config_list
# #         )

# #         counselor = autogen.UserProxyAgent(
# #             name="counselor",
# #             system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions.",
# #             is_termination_msg=lambda x: self.check_termination(x),
# #             human_input_mode="NEVER",
# #             code_execution_config={"work_dir": "coding", "use_docker": False},
# #             llm_config=self.config_list
# #         )

# #         FAQ_agent = autogen.AssistantAgent(
# #             name="suggests_retrieve_function",
# #             is_termination_msg=lambda x: self.check_termination(x),
# #             system_message="Suggests function to use to answer HIV/PrEP counselling questions",
# #             human_input_mode="NEVER",
# #             code_execution_config={"work_dir": "coding", "use_docker": False},
# #             llm_config=self.config_list
# #         )

# #         self.agents = [counselor, FAQ_agent, patient]

# #         # Define the wrapper function
# #         def answer_question_wrapper(user_question: str):
# #             return self.answer_question(user_question)

# #         # Register the wrapper function with autogen
# #         autogen.agentchat.register_function(
# #             answer_question_wrapper,
# #             caller=FAQ_agent,
# #             executor=counselor,
# #             name="answer_question",
# #             description="Retrieves embedding data content to answer user's question.",
# #         )

# #         # Initialize the GroupChat
# #         group_chat = autogen.GroupChat(
# #             agents=self.agents,
# #             messages=[],
# #         )

# #         # Initialize the AutoGen GroupChatManager
# #         self.group_chat_manager = autogen.GroupChatManager(
# #             groupchat=group_chat,
# #             llm_config=self.config_list,
# #             system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information."
# #         )

# #         # self.group_chat_manager.initiate_chat(
# #         #     patient,
# #         #     message="How can I help you?",
# #         # )

# #     async def handle_user_message(self, user_message: str, connection_id: str) -> str:
# #         """
# #         Handle the user message and return the response.
# #         """
# #         # Define history (can be fetched from a database or in-memory store)
# #         history: List[Dict[str, Any]] = []

# #         # Process the message using AutoGenChatManager
# #         response_message = self.websocket_manager.chat(
# #             message=user_message,
# #             history=history,
# #             workflow=None,  # Define or load your workflow configuration
# #             connection_id=connection_id,
# #             user_dir="user_data"  # Define the user directory
# #         )

# #         print(f"Generated response: {response_message.content}")

# #         return response_message.content
