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

# assess HIV funtion
def assess_hiv_risk(message):
    questions = {
        'sex_with_men': "Have you had unprotected sexual intercourse with men in the past 3 months? (Yes/No): ",
        'multiple_partners': "Have you had multiple sexual partners in the past 12 months? (Yes/No): ",
        'iv_drug_use': "Have you used intravenous drugs or shared needles? (Yes/No): ",
        'partner_hiv_positive/unknown': "Do you have a sexual partner who is HIV positive/ has unknown HIV status? (Yes/No): ",
        'std_history': "Have you been diagnosed with a sexually transmitted disease (STD) in the past 12 months? (Yes/No): ",
        # Add more questions as necessary
    }
    
    high_risk = False
    responses = {}
    
    print("HIV Risk Assessment Questionnaire\n")
    
    for key, question in questions.items():
        response = input(question).strip().lower()
        responses[key] = response
        if response == 'yes':
            high_risk = True
    
    if high_risk:
        print("\nBased on your responses, you may be at a higher risk for HIV. It is recommended to consider taking PrEP to protect from HIV infection.")
    else:
        print("\nBased on your responses, your risk for HIV appears to be lower. However, continue to practice safe behaviors and consult a healthcare professional for personalized advice.")
    
    return responses





# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
    "functions": [
    {
        "name": "assess_hiv_risk",
        "description": "Ask patients a couple of questions to assess their HIV risk",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "questions asks to assess patient's HIV risk",
                },
            },
            "required": ["message"],
        },
    },
    
],
}


counselor = autogen.AssistantAgent(
    name="assistant",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    system_message="You are an HIV PrEP counselor. You will be guided by the HIV provider to assess patients' risk and conduct motivational interviewing for PrEP if indicated",
)


def initialize_agents(llm_config):

    # create an AssistantAgent named "assistant"
    counselor = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "cache_seed": 41,  # seed for caching and reproducibility
            "config_list": config_list,  # a list of OpenAI API configurations
            "temperature": 0,  # temperature for sampling
        },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
        system_message="You are an HIV PrEP counselor. You will be guided by the HIV provider to assess patients' risk and conduct motivational interviewing for PrEP if indicated",
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

    return counselor, patient

# the assistant receives a message from the user_proxy, which contains the task description
counselor, patient = initialize_agents(config_list)
chat_res = patient.initiate_chat(
    counselor,
    message="""I would like to assess my HIV risk""",
    summary_method="reflection_with_llm",
    system_message="You are an HIV PrEP counselor. You will be guided by the HIV provider to assess patients' risk and conduct motivational interviewing for PrEP if indicated",
)