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

# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

config_list = [
    {
        "model": "gpt-4", 
        "api_key": os.getenv(api_key)
        }
        ]




# Function description
llm_config_counselor = {
    "temperature": 0,
    "timeout": 300,
    "cache_seed": 43,
    "config_list": config_list,
    "functions": [
    {
        "name": "search_provider",
        "description": "Use the ZIP code provided to find the nearest provider",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "ZIP code of the patient to use to find the nearest PrEP provider",
                },
            },
            "required": ["message"],
        },
    },
    
],
}

# Search provider assistant agent
search_bot = autogen.AssistantAgent(
    name="search_bot",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    system_message="When asked for a counselor, only suggest the function you have been provided with and use the ZIP code provided as an argument.",
    is_termination_msg=lambda x: check_termination(x),
)


# Search provider user proxy agent
def check_termination(x):
    print(f"Message content: {x}")
    return x.get("content", "").rstrip().endswith("TERMINATE")

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
  
    code_execution_config={"work_dir":"coding", "use_docker":False},
    system_message="Use the results from the function call to provide a list of nearby counselors"
)



@user_proxy.register_for_execution()
@search_bot.register_for_llm(description="Nearest provider finder")
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
    

# # Testing if search_provider works
# search_provider("02906") 

user_proxy.initiate_chat(
    search_bot,
    message="What are the nearest PrEP Providers to 02906 ZIP code"
)




# Agents for the conversation


def initialize_agents(llm_config):

    # create an AssistantAgent named "assistant"
    counselor = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "cache_seed": 41,  # seed for caching and reproducibility
            "config_list": config_list,  # a list of OpenAI API configurations
            "temperature": 0,  # temperature for sampling
        },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
        system_message="You are an HIV PrEP counselor. You will search the internet for the nearest PrEP provider",
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
        function_map={"search_provider":search_provider}
    )



    return counselor, patient

# the assistant receives a message from the user_proxy, which contains the task description
counselor, patient = initialize_agents(config_list)
# initialzie the conversation
patient.initiate_chat(
    counselor,
    message="Assess my HIV risk",
    summary_method="reflection_with_llm",
    system_message="You are an HIV PrEP counselor.",
)