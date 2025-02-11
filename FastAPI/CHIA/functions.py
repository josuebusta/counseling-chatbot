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
from CHIA.evaluation import evaluate_counseling_response



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
    """
    try:
        print("Initializing Chrome options...")
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless=new')  # Updated headless mode
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.binary_location = '/usr/bin/google-chrome-stable'

        print("Setting up Chrome service...")
        service = Service(executable_path='/usr/local/bin/chromedriver')
        
        print("Creating Chrome driver...")
        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome driver created successfully")
        except Exception as e:
            print(f"Failed to create Chrome driver: {str(e)}")
            # Try to get more detailed error information
            import subprocess
            print("Chrome version:", subprocess.getoutput('google-chrome --version'))
            print("ChromeDriver version:", subprocess.getoutput('chromedriver --version'))
            print("Chrome binary location:", subprocess.getoutput('which google-chrome-stable'))
            print("ChromeDriver location:", subprocess.getoutput('which chromedriver'))
            raise

        try:
            print(f"Navigating to preplocator.org for zip code {zip_code}...")
            driver.get("https://preplocator.org/")
            print("Page loaded successfully")
            time.sleep(5)  # Increased wait time

            # Print page source for debugging
            print("Page source length:", len(driver.page_source))
            
            print("Looking for search box...")
            search_box = driver.find_element(By.CSS_SELECTOR, "input[type='search']")
            print("Search box found")
            
            search_box.clear()
            search_box.send_keys(zip_code)
            print(f"Entered zip code: {zip_code}")

            print("Looking for submit button...")
            submit_button = driver.find_element(By.CSS_SELECTOR, "button.btn[type='submit']")
            print("Submit button found")
            
            submit_button.click()
            print("Clicked submit button")
            
            time.sleep(5)  # Wait for results to load

            # Rest of your existing code...
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

            if not extracted_data:
                return "I couldn't find any providers in that area. Would you like to try a different ZIP code?"

            # Create DataFrame and filter results
            df = pd.DataFrame(extracted_data)
            df['Distance'] = df['Distance'].str.replace(r'[^\d.]+', '', regex=True)
            df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
            filtered_df = df[df['Distance'] <= 30].nsmallest(5, 'Distance')  

            if filtered_df.empty:
                return "I couldn't find any providers within 30 miles of that ZIP code. Would you like to try a different ZIP code?"

            # Format results
            formatted_results = "Here are the 5 closest providers to you:\n\n"
            for _, provider in filtered_df.iterrows():
                formatted_results += f"{provider['Name']}\n"
                formatted_results += f"- Address: {provider['Address']}\n"
                formatted_results += f"- Phone: {provider['Phone']}\n"
                formatted_results += f"- Distance: {provider['Distance']} miles\n\n"
            
            formatted_results += "Would you like any additional information about these providers?"
            
            return formatted_results

        except Exception as e:
            print(f"Error during search: {str(e)}")
            print("Page source:", driver.page_source)  # This will help debug page loading issues
            raise
            
    except Exception as e:
        print(f"Error in search_provider: {str(e)}")
        return f"I'm sorry, I couldn't find any providers near you. Technical Error: {str(e)}"
    
    finally:
        if 'driver' in locals():
            print("Closing Chrome driver...")
            driver.quit()

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
    answer = ""
    try:
        # # Step 1: Ask if they want support
        # await websocket.send_text(
        #     "I understand you're feeling stressed. Would you like additional support from a human research assistant?"
        # )
        
        # Wait for initial response
        # try:
        #     response = await websocket.receive_text()
        #     # if "chat_id" not in response:     
        #     print("Initial user response:", response)
            
        #     # Parse the response
        #     response_json = json.loads(response)
        #     answer = response_json.get("content", "").lower()
        # except json.JSONDecodeError:
        #     await websocket.send_text("I didn't understand that. Could you please respond with 'yes' or 'no'?")
        #     return "Invalid response format."
        
        # # Step 2: Check if the user agrees
        # if "yes" not in answer:
        #     return "I understand. Please let me know if you change your mind. What else can I help you with?"
        
        # Step 3: Ask for the support type
        await websocket.send_text(
            "To help connect you with the right support:\n"
            "- What type of support would be most helpful? (emotional, financial, medical support, etc.)"
        )
        print("Sent support type question.")
        
        # Wait for response with name and support type
        try:
            response = await websocket.receive_text()
            print("Support type response:", response)
            
            # Parse the response
            response_json = json.loads(response)
            info = response_json.get("content", "")
        except json.JSONDecodeError:
            await websocket.send_text("I didn't understand that. Could you please rephrase your response?")
            return "Invalid response format."
        
        # Parse name and support type
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

        return f"Thank you for sharing that. When your chat session ends, a research assistant will reach out to provide {support_type} support. What else can I help you with?"

    except Exception as e:
        print(f"Error recording support request: {e}")
        # return "I'm having trouble recording your request. Please let me know if you'd like to try again."


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


async def get_chat_history():
    try:

        max_chats = 50
        non_evaluated_chats = supabase.table("chats") \
            .select("id") \
            .is_("chat_evaluation_sent", False) \
            .execute()

        chat_ids = [chat["id"] for chat in non_evaluated_chats.data or []]
        
        if not chat_ids:
            print("No non-evaluated chats found.")
            return None
        chat_ids = chat_ids[:max_chats]

        for chat_id in chat_ids:
            current_time = datetime.now(timezone.utc)
      
            chat_response = supabase.table("chats")\
                            .select("updated_at", "created_at")\
                            .eq("id", chat_id.strip())\
                            .execute()
            
            updated_at_str = chat_response.data[0]['updated_at']
            if not updated_at_str:
                updated_at_str = chat_response.data[0]['created_at']
            if updated_at_str:
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            
            else:
                print("No updated_at found for chat_id:", chat_id)
                continue
                
            print("updated at", updated_at)
            if (current_time - updated_at).total_seconds() > 300:
            
                history_response = supabase.table("messages") \
                    .select("content") \
                    .eq("chat_id", chat_id) \
                    .execute()

                chat_history = [msg["content"] for msg in history_response.data or []]

                if not chat_history:
                    print("No chat messages found.")
                    return None

                # Evaluate chat history
                evaluate_counseling_response(str(chat_id), chat_history)
                print(f"Evaluated {len(chat_history)} chat messages")

                # Mark chats as evaluated
                supabase.table("chats") \
                    .update({"chat_evaluation_sent": True}) \
                    .in_("id", chat_ids) \
                    .execute()

        return chat_history

    except Exception as e:
        print(f"Error processing chat history: {e}")
        return None




async def check_inactive_chats():
    try:
    
        response = supabase.table("support_requests")\
            .select("*, chats(updated_at)")\
            .eq("notified", False)\
            .execute()
        
       
        support_requests = response.data
        print("support_requests", support_requests)
        if not support_requests:
            print("No support requests found.")
            return

        #current time
        current_time = datetime.now(timezone.utc)

        # Filter support requests where the last activity was more than 5 minutes ago
        updates = []
        for request in support_requests:
            # print("request", request)
            try:
                # Only process if chat_id exists
                if request['chat_id']:
                    # print("chat_id", request['chat_id'])
                    # print("chat id exists")
                    # Fetch chat data separately
                    # chat_response = supabase.table("chats")\
                    #     .select("*")\
                    #     .eq("id", "e94b2f70-125d-4d6b-aa78-886c806dfa17")\
                    #     .execute()
                    chat_response = supabase.table("chats")\
                        .select("updated_at")\
                        .eq("id", request['chat_id'].strip())\
                        .execute()
                    # print("chat_response", chat_response)

        
                        
          
                    
                    updated_at_str = chat_response.data[0]['updated_at']
                    if updated_at_str:
                        updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                    else:
                        print("No updated_at found for chat_id:", request['chat_id'])
                        continue
                        
                    print("updated at", updated_at)
                    if (current_time - updated_at).total_seconds() > 300:
                        updates.append(request["id"])
                        print("updates", updates)
                        # send chat history evaluation to research assistant
                        
                        print(f"Adding request {request['id']} to updates - inactive for more than 5 minutes")

            except Exception as e:
                print(f"Error processing request {request['id']}: {e}")
                continue

        # Update the notified field for the filtered support requests
        if updates:
            for request_id in updates:
                client_id = supabase.table("chats")\
                    .select("user_id")\
                    .eq("id", request['chat_id'])\
                    .execute()
                
                notify_research_assistant("test", request['support_type'], "amarisgrondin@gmail.com", client_id)
                supabase.table("support_requests")\
                    .update({"notified": True})\
                    .eq("id", request_id)\
                    .execute()
                print(f"Support request {request_id} updated successfully.")
        else:
            print("No support requests need updating.")

    except Exception as e:
        print(f"An error occurred: {e}")

