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


# CONFIGURATION 

# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

config_list = [
    {
        "model": "gpt-4", # explore newest model - o1-mini
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



# AGENTS INITALIZATION


# # Search provider assistant agent to suggest the function to the search agent
# search_bot = autogen.AssistantAgent(
#     name="search_bot",
#     llm_config={
#         "cache_seed": 41,  # seed for caching and reproducibility
#         "config_list": config_list,  # a list of OpenAI API configurations
#         "temperature": 0,  # temperature for sampling
#     },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
#     system_message="When asked for a counselor, only suggest the function you have been provided with and use the ZIP code provided as an argument. If not ZIP code has been provided, ask for the ZIP code.",
#     is_termination_msg=lambda x: check_termination(x),
#     code_execution_config={"work_dir":"coding", "use_docker":False},
# )

# # Executes the search_provider function
# search = autogen.UserProxyAgent(
#     name="search",
#     human_input_mode="NEVER",
#     max_consecutive_auto_reply=10,
  
#     code_execution_config={"work_dir":"coding", "use_docker":False},
#     system_message="Use the results from the function call to provide a list of nearby counselors"
# )



# Main counselor - answers general questions 
counselor = autogen.UserProxyAgent(
    name="counselor",
    system_message="You are an HIV PrEP counselor. Use the context you received to give a concise answer to the question asked by the patient. DO NOT print the context or the message you received in your answer. Just respond to the question.",
    is_termination_msg=lambda x: check_termination(x),
    human_input_mode="NEVER",
    code_execution_config={"work_dir":"coding", "use_docker":False},
)

# counselor_aid - gives the counselor some context
counselor_aid = RetrieveUserProxyAgent(
    name="counselor aid",
    is_termination_msg=lambda x: check_termination(x),
    system_message="Assistant who has extra content retrieval power for information about HIV and PrEP.",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    retrieve_config={
        "task": "qa",
        "docs_path": "/Users/amaris/Desktop/AI_coder/counselling-chatbot/CHIA/HIV_PrEP_knowledge_embedding.json",
        "get_or_create": True
    },
    code_execution_config={"work_dir":"coding", "use_docker":False},
)

# Search provider user proxy agent (Debugging purposes)
def check_termination(x):
    print(f"Message content: {x}")
    return x.get("content", "").rstrip().endswith("TERMINATE")



# Patient (Chatbot-user)
patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    #is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    # code_execution_config={
    #     "executor": LocalCommandLineCodeExecutor(work_dir="coding"), 
    # },
    code_execution_config={"work_dir": "coding", "use_docker": False},
)


# # HIV assessment questions assistant to suggest the function to the assessment agent
# assessment_bot = autogen.AssistantAgent(
#     name="assessment_bot",
#     llm_config={
#         "cache_seed": 41,  # seed for caching and reproducibility
#         "config_list": config_list,  # a list of OpenAI API configurations
#         "temperature": 0,  # temperature for sampling
#     },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
#     system_message="When a patient asks to assess HIV risk, only suggest the function you have been provided with.",
#     is_termination_msg=lambda x: check_termination(x),
# )
counselor_bot = autogen.AssistantAgent(
    name="counselor_bot",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    # Make system message very clear
    system_message="When a patient about counseling for HIV/PrEP and the questions, provide the counselor with the content retrieved from the counselor_aid agent. DO NOT print t",
    is_termination_msg=lambda x: check_termination(x),
)


# # Executes the assess_risk function
# assessment = autogen.UserProxyAgent(
#     name="assessment",
#     human_input_mode="NEVER",
#     max_consecutive_auto_reply=10,
#     code_execution_config={"work_dir":"coding", "use_docker":False},
#     system_message="Use the function call to ask the patient some questions about their HIV risk and assess their HIV risk based on the function",
# )


def retrieve_content(message: str, n_results: int = 1) -> str:
    counselor_aid.n_results = n_results  # Set the number of results to be retrieved.
    _context = {"problem": message, "n_results": n_results}
    ret_msg = counselor_aid.message_generator(counselor_aid, None, _context)
    return ret_msg or message

for caller in [counselor_bot ]:
    d_retrieve_content = caller.register_for_llm(
        description="retrieve content for counselling HIV/PrEP", api_style="function"
    )(retrieve_content)

for executor in [counselor]:
    executor.register_for_execution()(d_retrieve_content)


# @search.register_for_execution()
# @search_bot.register_for_llm(description="Nearest provider finder")
def search_provider(zip_code: str):
    # Set the path to the WebDriver
    # Initialize Chrome options
    chrome_options = Options()
    # Use ChromeDriverManager to get the ChromeDriver path
    driver_path = ChromeDriverManager().install()
    
    service = Service(driver_path)

    driver = webdriver.Chrome(service=service, options=chrome_options.add_argument('--headless'))
    # Open the website
    driver.get("https://preplocator.org/")

    # Wait for the page to load
    time.sleep(2)

    # Find the search box and enter the ZIP code
    search_box = driver.find_element(By.CSS_SELECTOR, "input[type='search']")
    search_box.clear()
    search_box.send_keys(zip_code)

    # Find the submit button and click it
    submit_button = driver.find_element(By.CSS_SELECTOR, "button.btn[type='submit']")
    submit_button.click()

    # Wait for results to load (adjust the sleep time as needed)
    time.sleep(5)
    # Now scrape the locator-results-item elements
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    results = soup.find_all('div', class_='locator-results-item')
    
    extracted_data = []
    
    for result in results:
        # Extract the relevant information from each result item
        name = result.find('h3').text.strip() if result.find('h3') else 'N/A'
        details = result.find_all('span')
        address = details[0].text.strip() if len(details) > 0 else 'N/A'
        phone = details[1].text.strip() if len(details) > 1 else 'N/A'
        distance_with_label = details[2].text.strip() if len(details) > 2 else 'N/A'
        distance = distance_with_label.replace('Distance from your location:', '').strip() if distance_with_label != 'N/A' else 'N/A'
        extracted_data.append({
            'Name': name,
            'Address': address,
            'Phone': phone,
            'Distance': distance
        })
    
    driver.quit()
    
        
    df = pd.DataFrame(extracted_data)
    df['Distance'] = df['Distance'].str.replace(r'[^\d.]+', '', regex=True)
    df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
    # Filter for locations within 30 miles
    print(df[df['Distance'] <=30])
    filtered_df = df[df['Distance'] <=30]
    return filtered_df.to_json(orient='records')
    # Print or process the extracted data


# FUNCTION TO ASSESS PATIENT'S HIV RISK
# @assessment.register_for_execution()
# @assessment_bot.register_for_llm(description="Assesses HIV risk")
def assess_hiv_risk():
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



# INITIALIZE THE GROUP CHAT

group_chat = autogen.GroupChat(
    agents=[counselor, counselor_bot, patient],
            # , search_bot, search, assessment, assessment_bot], 
    messages=[], 
    max_round=12
    # ,speaker_selection_method="round_robin"
    )

manager = autogen.GroupChatManager(groupchat=group_chat, llm_config= llm_config_counselor, )


patient.initiate_chat(
    manager,
    message="How does the intersection of cultural identity and sexual orientation affect attitudes towards PrEP?",
)