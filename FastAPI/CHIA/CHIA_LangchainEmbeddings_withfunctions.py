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
from functions import assess_hiv_risk, search_provider
from retrieval import qa_chain

# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load environment variables from .env file
dotenv_path = 'chatbot-env'
load_dotenv(dotenv_path=dotenv_path)
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    raise ValueError("API key not found. Please set OPENAI_API_KEY in your .env file.")

config_list = {
    "model": "gpt-4o-mini", 
    "api_key": api_key  # Directly use the api_key variable
}

# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
}


# FUNCTION TO CHECK TERMINATION
# Search provider user proxy agent (Debugging purposes)
def check_termination(x):
    """
    Checks if the message content ends with "TERMINATE" to determine if the conversation should end.

    Parameters:
    x (dict): A dictionary containing the message content

    Returns:
    bool: True if the message ends with "TERMINATE", False otherwise
    """

    print(f"Message content: {x}")
    return x.get("content", "").rstrip().endswith("TERMINATE")


def answer_question(question: str) -> str:
    """
    Answer a question based on HIV PrEP knowledge base.

    :param question: The question to answer.
    :return: The answer as a string.
    """
    result = qa_chain.invoke({"query": question})
    return result.get("result", "I'm sorry, I couldn't find an answer to that question.")


# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=100,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    llm_config=config_list
)


# AGENTS INITALIZATION
# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=100,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    llm_config=config_list
)


# Main counselor - answers general questions 
counselor = autogen.UserProxyAgent(
    name="counselor",
    system_message="You are an HIV PrEP counselor. Call the function provided to answer user's questions. ",
    is_termination_msg=lambda x: check_termination(x),
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
    llm_config=config_list
)

# counselor_aid - gives the counselor some context
FAQ_agent = autogen.AssistantAgent(
    name="suggests_retrieve_function",
    is_termination_msg=lambda x: check_termination(x),
    system_message="Suggests function to use to answer HIV/PrEPcounselling questions",
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
    llm_config=config_list
)

autogen.agentchat.register_function(
    answer_question,
    caller=FAQ_agent,
    executor=counselor,
    name="answer_question",
    description="Retrieves embedding data content to answer user's question.",
)

autogen.agentchat.register_function(
    assess_hiv_risk,
    caller=FAQ_agent,
    executor=counselor,
    name="assess_hiv_risk",
    description="Assess patient's HIV risk when requested.",
)

autogen.agentchat.register_function(
    search_provider,
    caller=FAQ_agent,
    executor=counselor,
    name="search_provider",
    description="Searches for nearest provider when requested. If no ZIP code provided, asks for ZIP code.",
)

#INITIALIZE THE GROUP CHAT

group_chat = autogen.GroupChat(
    agents=[counselor, FAQ_agent, patient], 
    messages=[], 
    )

manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=config_list, system_message="When the patient specifically asks to assess their HIV risk, use the function suggested for that purpose. When the patient asks for their nearest provider, use the function suggested for that purpose. When asked any other question about HIV/PREP, always call the FAQ agent before to help the counselor answer. Then have the counselor answer the question concisely using the retrieved information.")

manager.initiate_chat(
    patient,
    message="How can I help you?",
)

