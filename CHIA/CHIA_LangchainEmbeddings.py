import os
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

# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class HIVPrEPCounselor:
    async def initialize(self):
        # Perform asynchronous initialization here
        await asyncio.sleep(1)
        
    def __init__(self):
# Load environment variables from .env file
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')

        if not self.api_key:
            raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

        self.config_list = {
            "model": "gpt-4o-mini", 
            "api_key": self.api_key  # Directly use the api_key variable
        }

        # Function description
        self.llm_config_counselor = {
            "temperature": 0,
            "timeout": 300,
            "cache_seed": 43,
            "config_list": self.config_list,
        }

        # Set up RAG components
        self.setup_rag()

        # Initialize agents
        self.initialize_agents()


        # FUNCTION TO CHECK TERMINATION
        # Search provider user proxy agent (Debugging purposes)
    def check_termination(self, x):
        """
        Checks if the message content ends with "TERMINATE" to determine if the conversation should end.

        Parameters:
        x (dict): A dictionary containing the message content

        Returns:
        bool: True if the message ends with "TERMINATE", False otherwise
        """

        print(f"Message content: {x}")
        return x.get("content", "").rstrip().endswith("TERMINATE")


    def setup_rag(self):
        # RAG prompt
        # Load the latest version of the prompt
        prompt = hub.pull("rlm/rag-prompt", api_url="https://api.hub.langchain.com")

        # Load documents from a URL
        # loader = JSONLoader('embeddings/HIV_PrEP_knowledge_embedding.json', jq_schema='.quiz', text_content=False)
        loader = WebBaseLoader("https://github.com/amarisg25/counselling-chatbot/blob/main/embeddings/HIV_PrEP_knowledge_embedding.json")
        data = loader.load()

        # Split documents into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_splits = text_splitter.split_documents(data)
        print(f"Number of splits: {len(all_splits)}")
        # Check the contents of all_splits
        # for i, split in enumerate(all_splits):
        #     print(f"Split Document {i}: {split}")

        # Store splits in the vector store
        vectorstore = Chroma.from_documents(documents=all_splits, embedding=OpenAIEmbeddings(openai_api_key=self.api_key))

        # Initialize the LLM with the correct model
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

 
        # Initialize RetrievalQA
        retriever = vectorstore.as_retriever()
        self.qa_chain = RetrievalQA.from_chain_type(
            llm, retriever= retriever, chain_type_kwargs={"prompt": prompt}
        )

    def answer_question(self, question: str) -> str:
        """
        Answer a question based on HIV PrEP knowledge base.

        :param question: The question to answer.
        :return: The answer as a string.
        """
        self.result = self.qa_chain.invoke({"query": question})
        return self.result.get("result", "I'm sorry, I couldn't find an answer to that question.")

    
    def initialize_agents(self):
        # AGENTS INITALIZATION
        # Patient (Chatbot-user)
        patient = autogen.UserProxyAgent(
            name="patient",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=10,
            code_execution_config={"work_dir": "coding", "use_docker": False},
            llm_config=self.config_list
        )


        # Main counselor - answers general questions 
        counselor = autogen.UserProxyAgent(
            name="counselor",
            system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions. ",
            is_termination_msg=lambda x: self.check_termination(x),
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list
        )

        # counselor_aid - gives the counselor some context
        FAQ_agent = autogen.AssistantAgent(
            name="suggests_retrieve_function",
            is_termination_msg=lambda x: self.check_termination(x),
            system_message="Suggests function to use to answer HIV/PrEPcounselling questions",
            human_input_mode="NEVER",
            code_execution_config={"work_dir":"coding", "use_docker":False},
            llm_config=self.config_list
        )

        self.agents = [counselor, FAQ_agent, patient]
        

        # Define the wrapper function
        def answer_question_wrapper(user_question: str):
            return self.answer_question(user_question)
        
        # Register the wrapper function with autogen
        autogen.agentchat.register_function(
            answer_question_wrapper,
            caller=FAQ_agent,
            executor=counselor,
            name="answer_question",
            description="Retrieves embedding data content to answer user's question.",
        )

        #INITIALIZE THE GROUP CHAT

        group_chat = autogen.GroupChat(
            agents= self.agents, 
            messages=[], 
            )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.config_list, system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information.")

        manager.initiate_chat(
            patient,
            message="How can I help you?",
        )

        def update_history(recipient, message, sender, config):
            self.agent_history.append({"sender": sender.name, "receiver": recipient.name, "message": message})

        for agent in self.agents:
            agent.register_reply(
                [autogen.Agent, None],
                reply_func=update_history, 
                config={"callback": None},
            )



if __name__ == "__main__":
    counselor = HIVPrEPCounselor()
    counselor.run()