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
import autogen
from autogen import AssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent


# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

config_list = [
    {
        "model": "gpt-4o", 
        "api_key": os.getenv(api_key)
        }
        ]

# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
}


assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant. Answer the questions based on the problem given and the content retrieved from the RAG.",
    llm_config=llm_config_counselor,
)



ragproxyagent = RetrieveUserProxyAgent(
    name="ragproxyagent",
    retrieve_config={
        "task": "qa",
        "docs_path": "CHIA/HIV_PrEP_knowledge_embedding.json",
        "get_or_create": True
    },
    code_execution_config={"work_dir":"coding", "use_docker":False},
)


ragproxyagent.initiate_chat(assistant, message="How does PrEP work for heterosexuals?")