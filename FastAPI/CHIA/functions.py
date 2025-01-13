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
from typing import Dict
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from fastapi import WebSocket

# async def assess_hiv_risk(websocket: WebSocket) -> str:
#     questions = {
#         'sex_with_men': "Have you had unprotected sexual intercourse with men in the past 3 months? (Yes/No): ",
#         'multiple_partners': "Have you had multiple sexual partners in the past 12 months? (Yes/No): ",
#         'iv_drug_use': "Have you used intravenous drugs or shared needles? (Yes/No): ",
#         'partner_hiv_positive/unknown': "Do you have a sexual partner who is HIV positive/ has unknown HIV status? (Yes/No): ",
#         'std_history': "Have you been diagnosed with a sexually transmitted disease (STD) in the past 12 months? (Yes/No): "
#     }

#     prompt = """It's completely understandable to feel concerned about your health, 
#     and I'm here to help you through this. To assess your HIV risk, I'll need to 
#     ask you a series of questions. Please remember that this is a safe space, 
#     and your feelings and experiences are important. Shall we begin? I'll be asking you some questions one at a time. \n\n"""

#     high_risk = False
#     responses = {}
#     result = ""
    
#     # await websocket.send_text("HIV Risk Assessment Questionnaire\n")

#     for key, question in questions.items():
#         # Send the question to the client
#         if key == "sex_with_men": # when it's the first question, send the prompt first
#             await websocket.send_text(prompt + question)
#         else:
#             await websocket.send_text(question)
#         # Receive the user's response through WebSocket
#         response = await websocket.receive_text()
#         response = response.strip().lower().strip('"')

#         responses[key] = response
#         if response == "yes":
#             high_risk = True
#             print("high_risk", high_risk)

#     # Send the assessment result based on the responses
    
#     if high_risk:
#         result = "The individual is at a higher risk for HIV. It is recommended to consider taking PrEP to protect from HIV infection."
#     else:
#         result = "The individual is at a lower risk for HIV. However, continue to practice safe behaviors and consult a healthcare professional for personalized advice."
#     print("result", result)
    # return result

async def assess_hiv_risk(websocket) -> str:
    """Conducts an HIV risk assessment through a series of questions."""
    questions = [
        "Have you had sex without condoms in the past 3 months?",
        "Have you had multiple sexual partners in the past 12 months?",
        "Have you used intravenous drugs or shared needles?",
        "Do you have a sexual partner who is HIV positive or whose status you don't know?",
        "Have you been diagnosed with an STI in the past 12 months?"
    ]
    
    await websocket.send_text("I understand you'd like to assess your HIV risk. I'll ask you a few questions - everything you share is confidential, and I'm here to help without judgment.")
    
    answers = []
    for question in questions:
        await websocket.send_text(question)
        response = await websocket.receive_text()
        answers.append(response.lower().strip())
    
    # Count risk factors
    risk_count = sum(1 for ans in answers if 'yes' in ans)
    
    # Generate appropriate response based on risk level
    if risk_count >= 1:
        return ("Based on your responses, you might benefit from PrEP (pre-exposure prophylaxis). "
                "This is just an initial assessment, and I recommend discussing this further with a healthcare provider. "
                "Would you like information about PrEP or help finding a provider in your area?")
    else:
        return ("Based on your responses, you're currently at lower risk for HIV. "
                "It's great that you're being proactive about your health! "
                "Continue your safer practices, and remember to get tested regularly. "
                "Would you like to know more about HIV prevention or testing options?")



# FUNCTION TO SEARCH FOR NEAREST PROVIDER
def search_provider(zip_code: str) -> Dict:
    """
    Searches for PrEP providers within 30 miles of the given ZIP code.
    
    Args:
        zip_code (str): The ZIP code to search for providers.
    
    Returns:
        str: A JSON string of provider information within 30 miles.
    """
    try:
        # Initialize Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Use ChromeDriverManager to get the ChromeDriver path
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Open the website
        driver.get("https://preplocator.org/")
        time.sleep(2)

        # Find the search box and enter the ZIP code
        search_box = driver.find_element(By.CSS_SELECTOR, "input[type='search']")
        search_box.clear()
        search_box.send_keys(zip_code)

        # Find the submit button and click it
        submit_button = driver.find_element(By.CSS_SELECTOR, "button.btn[type='submit']")
        submit_button.click()
        time.sleep(5)  # Wait for results to load

        # Parse the page content
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.find_all('div', class_='locator-results-item')
        
        # Extract information from each result item
        extracted_data = []
        for result in results:
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

        # Create DataFrame and filter for locations within 30 miles
        df = pd.DataFrame(extracted_data)
        df['Distance'] = df['Distance'].str.replace(r'[^\d.]+', '', regex=True)
        df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
        filtered_df = df[df['Distance'] <= 30]
        
        # Return data as JSON
        return filtered_df.to_json(orient='records')
    
    except Exception as e:
        return {"error": str(e)}

# # Example usage:
# print(search_provider("02912"))


async def assess_ttm_stage_single_question(websocket: WebSocket) -> str:
    """
    Assess the TTM stage of change based on a single validated question and response.
    
    Parameters:
    response (str): The individual's response to the question:
                    "Are you currently engaging in Prep uptake on a regular basis?"
                    Valid response options:
                    - "No, and I do not intend to start in the next 6 months" (Precontemplation)
                    - "No, but I intend to start in the next 6 months" (Contemplation)
                    - "No, but I intend to start in the next 30 days" (Preparation)
                    - "Yes, I have been for less than 6 months" (Action)
                    - "Yes, I have been for more than 6 months" (Maintenance)
    
    Returns:
    str: The stage of change (Precontemplation, Contemplation, Preparation, Action, Maintenance).
    """

    question = "Of course, I will ask you a single question to assess your status of change. \n Are you currently engaging in Prep uptake on a regular basis? Please respond with the number corresponding to your answer: \n 1. No, and I do not intend to start in the next 6 months. \n 2. No, but I intend to start in the next 6 months. \n 3. No, but I intend to start in the next 30 days. \n 4. Yes, I have been for less than 6 months. \n 5. Yes, I have been for more than 6 months."


    
    response = ""
    stage = ""
    
    # Map the response to the corresponding TTM stage
    while response not in ["1", "2", "3", "4", "5"]:
        await websocket.send_text(question)
        # Receive the user's response through WebSocket
        response = await websocket.receive_text()
        response = response.strip().lower().strip('"')
        if response == "1":
            stage = "Precontemplation"
        elif response == "2":
            stage = "Contemplation"
        elif response == "3":
            stage = "Preparation"
        elif response == "4":
            stage = "Action"
        elif response == "5":
            stage = "Maintenance"
        else:
            stage = "Unclassified"  # For unexpected or invalid responses
    
    answer = f"The individual is in the '{stage}' stage of change." if stage != "Unclassified" else "Please respond with the number corresponding to your answer: 1. No, and I do not intend to start in the next 6 months 2. No, but I intend to start in the next 6 months 3. No, but I intend to start in the next 30 days 4. Yes, I have been for less than 6 months 5. Yes, I have been for more than 6 months"
    return answer

