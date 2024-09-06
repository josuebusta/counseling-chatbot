#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 15 15:03:21 2024

@author: barbaratao
"""
from autogen.agentchat.contrib.capabilities.teachability import Teachability
import gradio as gr
import os
from pathlib import Path
import shutil
import openai
import autogen
import chromadb
import multiprocessing as mp
#from hiv_risk import assess_hiv_risk
#import search_provider
from autogen.retrieve_utils import TEXT_FORMATS, get_file_from_url, is_url
import os
from dotenv import load_dotenv
import os 

# Get API KEY from .env file
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')


os.environ["TOKENIZERS_PARALLELISM"] = "false"

config_list = [
    {
         'model':"gpt-4o-2024-05-13",
         'api_key' : 'OPENAI_API_KEY'
     }]

llm_config={
        "seed":42,
        "config_list":config_list,
        "temperature":0,
        "top_p":1

    }

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from bs4 import BeautifulSoup

def search_provider(zip_code):
    # Set path to the WebDriver
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
    results_locator = (By.CSS_SELECTOR, "div.locator-results-item")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located(results_locator))


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
    filtered_df = df[df['Distance'] <= 30]
    pd.set_option('display.max_columns', None)
    print(filtered_df)
    
    # Print or process the extracted data
    

search_provider("02906")


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

assess_hiv_risk()

llm_config_counselor = {
  "functions": [
    {
      "name": "assess_hiv_risk",
      "description": "ask patients a couple of questions to assess their HIV risk",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "a series of questions"
          }
        },
      }
    },
    {
      "name": "search_provider",
      "description": "Visit the website (https://preplocator.org/), input patients' Zipcode to search PrEP providers within a radius of 30 miles, and scrape website relevant content",
      "parameters": {
        "type": "object",
        "properties": {
          "zip_code": {
            "type": "string",
            "description": "visit the specified website and input Zip Code"
          }
        },
        "required": ["zip_code"]  
      }
    }
  ],
  "config_list": config_list
}

patients = autogen.UserProxyAgent(
    name="patients",
    code_execution_config={"last_n_messages": 2, "work_dir": "coding","use_docker":False},
    max_consecutive_auto_reply=0,
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    human_input_mode="TERMINATE",
    llm_config=llm_config,
)




counselor = autogen.AssistantAgent(
    name="counselor",
    llm_config=llm_config,
    code_execution_config=False,
    system_message="You are an HIV PrEP counselor. You will be guided by the HIV provider to assess patients' risk and conduct motivational interviewing for PrEP if indicated. Please give concise response at 8th-grade reading level, do not repeat previous mentioned information. Do not need to provide too much information about monitoring and communication with providers. Provide straightforward and clear response",
)

# Instantiate the Teachability capability. Its parameters are all optional.
teachability = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=False,
    path_to_db_dir="/Users/barbaratao/Documents/python_db/teachability_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)

teachability.add_to_agent(counselor)

counselor.initiate_chat(patients, message="How are you?", clear_history=True)
