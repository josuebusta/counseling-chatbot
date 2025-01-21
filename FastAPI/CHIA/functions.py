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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from supabase import create_client
import os
from datetime import datetime, timezone



async def assess_hiv_risk(websocket) -> str:
    """Conducts an HIV risk assessment through a series of questions."""
    questions = [
        """I'll help assess your HIV risk factors. This will involve a few questions about your sexual health and activities. Everything you share is completely confidential, and I'm here to help without judgment. Let's go through this step by step.\n First question: Have you had sex without condoms in the past 3 months?""",
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
        # filtered_df = df[df['Distance'] <= 30]
        filtered_df = df[df['Distance'] <= 30].nsmallest(5, 'Distance')  
        
        # Return data as JSON
        formatted_results = "Here are the 5 closest providers to you:\n\n"
            
        for _, provider in filtered_df.iterrows():
            formatted_results += f"{provider['Name']}\n"
            formatted_results += f"- Address: {provider['Address']}\n"
            formatted_results += f"- Phone: {provider['Phone']}\n"
            formatted_results += f"- Distance: {provider['Distance']} miles\n\n"
        
        formatted_results += "Would you like any additional information about these providers?"
        
        return formatted_results
        
    except Exception as e:
        return "I'm sorry, I couldn't find any providers near you. Please try again with a different ZIP code."

# # Example usage:
# print(search_provider("02912"))


# async def assess_ttm_stage_single_question(websocket: WebSocket) -> str:
#     """
#     Assess the TTM stage of change based on a single validated question and response.
    
#     Parameters:
#     response (str): The individual's response to the question:
#                     "Are you currently engaging in Prep uptake on a regular basis?"
#                     Valid response options:
#                     - "No, and I do not intend to start in the next 6 months" (Precontemplation)
#                     - "No, but I intend to start in the next 6 months" (Contemplation)
#                     - "No, but I intend to start in the next 30 days" (Preparation)
#                     - "Yes, I have been for less than 6 months" (Action)
#                     - "Yes, I have been for more than 6 months" (Maintenance)
    
#     Returns:
#     str: The stage of change (Precontemplation, Contemplation, Preparation, Action, Maintenance).
#     """

#     question = "Of course, I will ask you a single question to assess your status of change. \n Are you currently engaging in Prep uptake on a regular basis? Please respond with the number corresponding to your answer: \n 1. No, and I do not intend to start in the next 6 months. \n 2. No, but I intend to start in the next 6 months. \n 3. No, but I intend to start in the next 30 days. \n 4. Yes, I have been for less than 6 months. \n 5. Yes, I have been for more than 6 months."


    
#     response = ""
#     stage = ""
    
#     # Map the response to the corresponding TTM stage
#     while response not in ["1", "2", "3", "4", "5"]:
#         await websocket.send_text(question)
#         # Receive the user's response through WebSocket
#         response = await websocket.receive_text()
#         response = response.strip().lower().strip('"')
#         if response == "1":
#             stage = "Precontemplation"
#         elif response == "2":
#             stage = "Contemplation"
#         elif response == "3":
#             stage = "Preparation"
#         elif response == "4":
#             stage = "Action"
#         elif response == "5":
#             stage = "Maintenance"
#         else:
#             stage = "Unclassified"  # For unexpected or invalid responses
    
#     answer = f"The individual is in the '{stage}' stage of change." if stage != "Unclassified" else "Please respond with the number corresponding to your answer: 1. No, and I do not intend to start in the next 6 months 2. No, but I intend to start in the next 6 months 3. No, but I intend to start in the next 30 days 4. Yes, I have been for less than 6 months 5. Yes, I have been for more than 6 months"
#     return answer
async def assess_ttm_stage_single_question(websocket: WebSocket) -> str:
    question = """Of course, I will ask you a single question to assess your status of change. 
Are you currently engaging in Prep uptake on a regular basis? Please respond with the number corresponding to your answer: 
1. No, and I do not intend to start in the next 6 months.
2. No, but I intend to start in the next 6 months.
3. No, but I intend to start in the next 30 days.
4. Yes, I have been for less than 6 months.
5. Yes, I have been for more than 6 months."""

    await websocket.send_text(question)
    
    try:
        # Get response
        response = await websocket.receive_text()
        print(f"Received response: {response}")
        
        # Parse JSON response
        try:
            response_json = json.loads(response)
            # Extract content from JSON
            response_number = response_json.get("content", "")
        except json.JSONDecodeError:
            response_number = response

        # Map response to stage
        stage_map = {
            "1": "Precontemplation",
            "2": "Contemplation",
            "3": "Preparation",
            "4": "Action",
            "5": "Maintenance"
        }
        
        stage = stage_map.get(response_number, "Unclassified")
        
        if stage != "Unclassified":
            return f"Based on your response, you are in the '{stage}' stage of change regarding PrEP uptake. Let me explain what this means and discuss possible next steps."
        else:
            return "I didn't catch your response. Please respond with a number from 1 to 5 corresponding to your situation."
            
    except Exception as e:
        print(f"Error processing response: {e}")
        return "I'm having trouble processing your response. Please try again with a number from 1 to 5."

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 10 11:49:18 2024

@author: barbaratao
"""



def notify_research_assistant(client_name, support_type, assistant_email, client_id, smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465):
    """
    Function to notify research assistant when a client needs personal support.
    
    Parameters:
    client_name (str): Name of the client
    client_id (str): ID of the client
    support_type (str): Type of support needed (e.g., emotional, financial, etc.)
    assistant_email (str): Email address of the research assistant
    """
    print(f"Notifying research assistant {assistant_email} for client {client_name} (ID: {client_id}) with support type {support_type}.")
    
    # Set up email details
    sender_email = "t28184003@gmail.com"
    sender_password = "vnqs wulc clye ncjx"
    subject = f"Client {client_name} (ID: {client_id}) Needs Personal Support"
    
    # Create the email content
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = assistant_email
    message["Subject"] = subject
    
    # Customize the email body with details about the client and the support type
    body = f"""
    Hello,

    The client {client_name} (ID: {client_id}) requires personal support in the following area: {support_type}.

    Please follow up with the client as soon as possible to provide the necessary support.

    Thank you,
    Support Team
    """
    
    message.attach(MIMEText(body, "plain"))
    
    # Send the email
    try:
        # Establish a secure connection with the email server
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_password)
        
        # Send the email
        server.sendmail(sender_email, assistant_email, message.as_string())
        
        # Close the connection
        server.quit()
        print(f"Notification sent to {assistant_email} regarding client {client_name}.")
        
        return (f"A research assistant has been notified and will reach out to provide {support_type} support.")
    
    except Exception as e:
        print(f"Failed to send notification. Error: {e}")
        return (f"Failed to send notification. Error: {e}")
        


# Set up Supabase client
supabase = create_client(
    os.environ.get("NEXT_PUBLIC_SUPABASE_URL"),
    os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

async def record_support_request(websocket: WebSocket, chat_id: str) -> str:
    """
    Record in Supabase when a user requests support.
    """
    try:
        # Step 1: Ask if they want support
        await websocket.send_text("I understand you're feeling stressed. Would you like additional support from a human research assistant?")
        
        # Wait for response
        response = await websocket.receive_text()
        response_json = json.loads(response)
        answer = response_json.get("content", "").lower()
        
        # if "yes" not in answer:
        #     return "I understand. Please let me know if you change your mind."
            
        # Step 2: Get name and support type
        await websocket.send_text("To help connect you with the right support:\n- What name would you like me to use for you?\n- What type of support would be most helpful? (emotional, financial, medical support, etc.)")
        
        # Wait for response with name and support type
        response = await websocket.receive_text()
        response_json = json.loads(response)
        info = response_json.get("content", "")
        
        # Parse response
        parts = [part.strip() for part in info.split(',')]
        name = parts[0] if len(parts) >= 2 else "Anonymous"
        support_type = parts[1] if len(parts) >= 2 else parts[0]

        # Record in Supabase
        supabase.table("support_requests").insert({
            "client_name": name,
            "support_type": support_type,
            "created_at": datetime.now().isoformat(),
            "notified": False,
            "chat_id": chat_id
        }).execute()
        
        return f"Thank you for sharing that. When your chat session ends, a research assistant will reach out to provide {support_type} support."
        
    except Exception as e:
        print(f"Error recording support request: {e}")
        return "I'm having trouble recording your request. Please let me know if you'd like to try again."

# async def check_inactive_chats():
#     """
#     Background task to check for inactive chats and send notifications.
#     Runs periodically (e.g., every minute).
#     """
#     try:
#         # Get support requests that haven't been notified
#         result = supabase.table("support_requests")\
#             .select(
#                 "*, updated_at, chats!inner(updated_at)",
#                 count='exact'
#             )\
#             .eq("notified", False)\
#             .execute()

#         current_time = datetime.now(timezone.utc)

#         if result.data:  # Check if we got any results
#             for request in result.data:
#                 # Parse the timestamp from chat
#                 chat_timestamp = datetime.fromisoformat(request['chats']['updated_at'])
                
#                 # Check if inactive for more than 5 minutes
#                 if (current_time - chat_timestamp).total_seconds() > 3:
#                     # Send email notification
#                     await notify_research_assistant(
#                         request["client_name"],
#                         request["support_type"]
#                     )
                    
#                     # Update as notified
#                     supabase.table("support_requests")\
#                         .update({"notified": True})\
#                         .eq("id", request["id"])\
#                         .execute()


async def handle_inactivity(user_id, last_activity_time):
    """
    Handle the case where the user has been inactive for more than 5 minutes.
    This could involve sending an email or logging the event.
    """
    print(f"User {user_id} has been inactive since {last_activity_time}. Triggering action.")
    
    # Implement your logic to send the email or take the necessary action
    # For example, call your email service here
    # email_service.send_inactivity_email(user_id)

    # Example log:
    print(f"Sending email notification to user {user_id} about inactivity since {last_activity_time}")



# async def check_inactive_chats():
#     try:
#         # Fetch last activity times from chats and join with support_requests
#         response = supabase.table("support_requests")\
#             .select("*, chats!support_requests_chat_id_fkey(id, updated_at)")\
#             .eq("notified", False)\
#             .execute()
        
#         print(response)
#         # Access the data attribute from the response
#         data = response.data
#         print(data)
        
#         if not data:
#             print("No inactive chats found.")
#             return

#         # Current time
#         current_time = datetime.now()

#         # Loop through the results and check for inactivity
#         for record in data:
#             if 'chats' in record and record['chats']:
#                 chat_id = record['chats'][0].get('chat_id')
#                 last_activity_time = datetime.fromisoformat(record['chats'][0].get('updated_at'))
#                 print("last_activity_time", last_activity_time)
                
#                 # Calculate time difference
#                 time_diff = current_time - last_activity_time
#                 print("time_diff", time_diff)
#                 print("current_time", current_time)
#                 print("last_activity_time", last_activity_time)
#                 if time_diff > timedelta(minutes=5):
#                     # Handle inactivity (e.g., trigger email or log it)
#                     await handle_inactivity(chat_id, last_activity_time)

#                     # Optionally, update the `notified` field in support_requests
#                     supabase.table("support_requests") \
#                         .update({"notified": True}) \
#                         .eq("chat_id", record['id']) \
#                         .execute()
#     except Exception as e:
#         print(f"Error checking inactive chats: {e}")

# Initialize the Supabase client (replace with your project URL and API key)
async def check_inactive_chats():
    try:
        # Fetch support requests with related chat data where notified is False
        response = supabase.table("support_requests")\
            .select("id, chat_id, chats(updated_at)")\
            .eq("notified", False)\
            .execute()
        
        # Remove error check since response.error doesn't exist
        support_requests = response
        print("support_requests", support_requests)
        if not support_requests:
            print("No support requests found.")
            return

        # Get the current time
        current_time = datetime.now(timezone.utc)

        # Filter support requests where the last activity was more than 5 minutes ago
        updates = []
        for request in support_requests:
            chat = request
            print("chat", chat)
            if chat:
                updated_at = chat["updated_at"],
                if (current_time - updated_at).total_seconds() > 300:
                    updates.append(request["id"])

        # Update the notified field for the filtered support requests
        if updates:
            for request_id in updates:
                update_response = supabase.table("support_requests")\
                    .update({"notified": True})\
                    .eq("id", request_id)\
                    .execute()
                
                # Remove error check here as well
                print(f"Support request {request_id} updated successfully.")
        else:
            print("No support requests need updating.")

    except Exception as e:
        print(f"An error occurred: {e}")