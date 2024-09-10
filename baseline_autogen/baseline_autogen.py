from IPython.display import Image, display

import autogen
from autogen.coding import LocalCommandLineCodeExecutor
from openai import OpenAI
from dotenv import load_dotenv
import os


# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

config_list = [
    {
        "model": "gpt-4", 
        "api_key": os.getenv(api_key)
        }
        ]



# create an AssistantAgent named "assistant"
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    system_message='You are an HIV/PrEP counselor.'
)

# create a UserProxyAgent instance named "user_proxy"
patient = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        # the executor to run the generated code
        "executor": LocalCommandLineCodeExecutor(work_dir="coding"), # different from video
    },
)

# the assistant receives a message from the user_proxy, which contains the task description
chat_res = patient.initiate_chat(
    assistant,
    message="I would like to assess my HIV risk",
    summary_method="reflection_with_llm",
)