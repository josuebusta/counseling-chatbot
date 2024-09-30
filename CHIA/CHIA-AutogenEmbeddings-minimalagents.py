from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os 
from openai import OpenAI
from IPython.display import Image, display
import autogen
from autogen.coding import LocalCommandLineCodeExecutor
from openai import OpenAI
from dotenv import load_dotenv
import os
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from functions import assess_hiv_risk, search_provider


# CONFIGURATION 
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

config_list = {
        "model": "gpt-4o-mini", 
        "api_key": os.getenv(api_key)
        }
        
# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
}


# AGENTS INITALIZATION
# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    llm_config=config_list
)

# Main counselor - answers general questions 
counselor = autogen.UserProxyAgent(
    name="counselor",
    system_message="You are an HIV PrEP counselor. DO NOT use the internet to answer. Instead, use the context you received to give answer to the question asked by the patient. ",
    is_termination_msg=lambda x: check_termination(x),
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
    llm_config=config_list
)

# counselor_aid - gives the counselor some context
FAQ_retrieve_agent = RetrieveUserProxyAgent(
    name="counselor_aid",
    is_termination_msg=lambda x: check_termination(x),
    system_message="Assistant who has extra content retrieval power for information about HIV and PrEP.",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    retrieve_config={
        "task": "default",
        "docs_path": "embeddings/HIV_PrEP_knowledge_embedding.json",
        "get_or_create": True
    },
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

# FUNCTION TO RETRIEVE CONTENT FROM COUNSELOR AID
def retrieve_content(message: str, n_results: int = 1) -> str:
    """
    Retrieves content for counselling HIV/PrEP using the counselor_aid agent.

    Parameters:
    message (str): The query or problem statement
    n_results (int): The number of results to retrieve (default: 1)

    Returns:
    str: The retrieved content or the original message if no content is found
    """

    FAQ_retrieve_agent.n_results = n_results  # Set the number of results to be retrieved.
    _context = {"problem": message, "n_results": n_results}
    ret_msg = FAQ_retrieve_agent.message_generator(FAQ_retrieve_agent, None, _context)
    print(ret_msg)
    return ret_msg or message


autogen.agentchat.register_function(
    retrieve_content,
    caller=FAQ_agent,
    executor=counselor,
    name="retrieve_content",
    description="Rertrieves embedding data content to answer user's question.",
)

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



#INITIALIZE THE GROUP CHAT

group_chat = autogen.GroupChat(
    agents=[counselor, FAQ_agent, patient], 
    messages=[], 
    )

manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=config_list, system_message="When asked a question about HIV/PREP, always call the FAQ agent before to help the counselor answer")

manager.initiate_chat(
    patient,
    message="How can I help you?",
)