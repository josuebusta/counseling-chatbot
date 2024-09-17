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
from autogen import register_function

os.environ["TOKENIZERS_PARALLELISM"] = "false"


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


assistant_bot = autogen.AssistantAgent(
    name="assistant_bot",
    system_message="When asked questions about HIV/PrEP, only suggest the function you have been provided with and use the user's message provided as an argument.",
    llm_config=llm_config_counselor,
)

assistant = autogen.UserProxyAgent(
    name="assistant",
    system_message="You are a HIV counselor. Answer all questions related to HIV and prep except if the user asks to assess their HIV risk based on the response of the function call. ONLY provide the answer to the question.",
    llm_config=llm_config_counselor,
    code_execution_config={"work_dir":"coding", "use_docker":False},
    human_input_mode="NEVER"
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

patient = autogen.UserProxyAgent(
    name="patient",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=10,
    #is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "executor": LocalCommandLineCodeExecutor(work_dir="coding"), 
    },
)

# Search provider user proxy agent (Debugging purposes)
def check_termination(x):
    print(f"Message content: {x}")
    return x.get("content", "").rstrip().endswith("TERMINATE")

# Search provider assistant agent to suggest the function to the search agent
search_bot = autogen.AssistantAgent(
    name="search_bot",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    system_message="When asked for a counselor, only suggest the function you have been provided with and use the ZIP code provided as an argument. If not ZIP code has been provided, ask for the ZIP code.",
    is_termination_msg=lambda x: check_termination(x),
)

# Executes the search_provider function
search = autogen.UserProxyAgent(
    name="search",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir":"coding", "use_docker":False},
    system_message="Use the results from the function call to provide a list of nearby counselors",
    silent=True
)

# HIV assessment questions assistant to suggest the function to the assessment agent
assessment_bot = autogen.AssistantAgent(
    name="assessment_bot",
    llm_config={
        "cache_seed": 41,  # seed for caching and reproducibility
        "config_list": config_list,  # a list of OpenAI API configurations
        "temperature": 0,  # temperature for sampling
    },  # configuration for autogen's enhanced inference API which is compatible with OpenAI API
    system_message="Only suggest the function you have been provided with when the patient asks to assess their HIV ris.",
    is_termination_msg=lambda x: check_termination(x),
)

# Executes the assess_risk function
assessment = autogen.UserProxyAgent(
    name="assessment",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir":"coding", "use_docker":False},
    system_message="Use the function call to ask the patient some questions about assessing their HIV risk based on the function",
)


def _reset_agents():
    assistant.reset()
    assistant_bot.reset()
    ragproxyagent.reset()
    patient.reset()
    assessment.reset()
    assessment_bot.reset()
    search.reset()
    search_bot.reset()


def call_rag_chat():
    _reset_agents()

    # FUNCTION TO SEARCH FOR CLOSE PROVIDERS
    # @search.register_for_execution()
    # @search_bot.register_for_llm(description="Nearest provider finder")
    def search_provider(zip_code: str) -> str:
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
   
    s_retrieve_content = search_bot.register_for_llm(
        name="search_provider", description="Finds nearest provider finder", api_style="function"
    )(search_provider)

    search.register_for_execution()(s_retrieve_content)


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
    a_retrieve_content = assessment_bot.register_for_llm(
    name="assess_hiv_risk", description="Assesses HIV risk", api_style="function"
    )(assess_hiv_risk)

    assessment.register_for_execution()(a_retrieve_content)


    # In this case, we will have multiple user proxy agents and we don't initiate the chat
    # with RAG user proxy agent.
    # In order to use RAG user proxy agent, we need to wrap RAG agents in a function and call
    # it from other agents.
    def retrieve_content(message: str, n_results: int = 1) -> str:
        ragproxyagent.n_results = n_results  # Set the number of results to be retrieved.
        _context = {"problem": message, "n_results": n_results}
        ret_msg = ragproxyagent.message_generator(ragproxyagent, assistant_bot, _context)
        print(ret_msg)
        return ret_msg or message

    ragproxyagent.human_input_mode = "NEVER"  # Disable human input for boss_aid since it only retrieves content.


    register_function(
        retrieve_content,
        caller=assistant_bot,  # The assistant agent can suggest calls to the calculator.
        executor=assistant,  # The user proxy agent can execute the calculator calls.
        name="retrieve_content",  # By default, the function name is used as the tool name.
        description="retrives context of the message",  # A description of the tool.
    )
 
    # r_retrieve_content = assistant.register_for_llm(
    #     name="retrieve_content", description="retrieve content for hiv/prep counseling", api_style="function"
    # )(retrieve_content)

    # assistant.register_for_execution()(r_retrieve_content)

    groupchat = autogen.GroupChat(
        agents=[assistant, assistant_bot, patient],
        messages=[],
        max_round=12,
        allow_repeat_speaker=False,
    )

    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_counselor)

    # Start chatting with the boss as this is the user proxy agent.
    patient.initiate_chat(
        manager,
        message="What is the breakdown of the cost for PrEP and ART?",
    )


call_rag_chat()