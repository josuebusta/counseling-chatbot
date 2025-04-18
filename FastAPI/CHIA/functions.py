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
from .accuracy_evaluation import evaluate_counseling_response
from .MI_evaluation import evaluate_motivational_interview
import asyncio


from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize OpenAI API
OpenAI.api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# List of questions
QUESTIONS = [
    "I'll help assess your HIV risk factors. This will involve a few questions about your sexual health and activities. Everything you share is completely confidential, and I'm here to help without judgment. Let's go through this step by step.\nFirst question: Have you had sex without condoms in the past 3 months?",
    "Have you had multiple sexual partners in the past 12 months?",
    "Have you used intravenous drugs or shared needles?",
    "Do you have a sexual partner who is HIV positive or whose status you don't know?",
    "Have you been diagnosed with an STI in the past 12 months?"
]



def classify_response(response, language):
    """Classifies response as affirmative, negative, uncooperative, or unsure using ChatGPT."""
    prompt = (f"In {language}, classify this response as 'affirmative', 'negative', 'stop' (if the user wants to stop or exit out of the assessment), 'clarification', or 'unsure': '{response}'. "
              f"Do not add extra words, just return the classification.")
    completion = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": prompt}]
    )
    return completion.choices[0].message.content.strip().lower()

def translate_question(question, language_code):
    """Translates a question into the user's detected language using ChatGPT."""
    prompt = f"Translate the following sentence to {language_code}: {question}"
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a translation assistant. Only return the translated question, no other text."},
                  {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

async def handle_clarification(websocket, question, user_response, language):
    """Recursive function to handle clarification requests."""
    # Generate clarification response
    clarification_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are here to clarify the question asked by the user. Please provide a clear answer of the information is being asked for."},
                      {"role": "user", "content": f"Question: {question}\nUser response: {user_response}\n\nPlease provide a clear answer of the information is being asked for. Also, re-ask the question initially asked at the end."}]
        )
    
    # Send the clarification response
    await websocket.send_text(clarification_response.choices[0].message.content)
    
    # Get the new response
    new_response = await websocket.receive_text()
    classification = classify_response(new_response, language)
    
    # If the user is still asking for clarification, recursively handle it
    if classification == "clarification":
        return await handle_clarification(websocket, question, new_response, language)
    
    # Otherwise, return the classification for further processing
    return classification, new_response

async def assess_hiv_risk(websocket, language_param):
    """Main function for administering questionnaire using websocket communication."""
    try:
        language = language_param
        print(f"[{language}]")
        
        # Track responses and questions for memo
        assessment_log = []
        affirmative_count = 0
        
        for question in QUESTIONS:
            if language != "English":
                question = translate_question(question, language)

            await websocket.send_text(question)
            user_response = await websocket.receive_text()
            classification = classify_response(user_response, language)
            
            # Log each Q&A
            assessment_log.append(f"Q: {question}\nA: {user_response}")

            if classification == "negative":
                await websocket.send_text("[Negative Response]")
            elif classification == "affirmative":
                await websocket.send_text("[Affirmative Response]")
                affirmative_count += 1
            elif classification == "stop":

               
                
                await websocket.send_text("[Stopping]")
                return translate_question("I understand you want to stop this assessment. Please let me know if you have any other questions.", language)
            elif classification == "clarification":
                # Use the recursive function to handle clarification
                classification, user_response = await handle_clarification(websocket, question, user_response, language)
                
                # Process the response after clarification
                if classification == "negative":
                    await websocket.send_text("[Negative Response]")
                elif classification == "affirmative":
                    await websocket.send_text("[Affirmative Response]")
                    affirmative_count += 1
                elif classification == "stop":
                    await websocket.send_text("[Stopping]")
                    return ("I understand you want to stop this assessment. Please let me know if you have any other questions.")
                else:
                    await websocket.send_text("[Unclear Response]")
            else:
                await websocket.send_text("[Unclear Response]")
        
        # Create recommendation
        if affirmative_count > 0:
            risk_level = "elevated"
            recommendation = (
                "Based on your responses, you might benefit from PrEP (pre-exposure prophylaxis). "
                "This is just an initial assessment, and I recommend discussing this further with a healthcare provider. "
                "Would you like information about PrEP or help finding a provider in your area?"
            )
        else:
            risk_level = "lower"
            recommendation = (
                "Based on your responses, you're currently at lower risk for HIV. "
                "It's great that you're being proactive about your health! "
                "Continue your safer practices, and remember to get tested regularly. "
                "Would you like to know more about HIV prevention or testing options?"
            )

        # Store complete assessment in teachability
        
        
        return translate_question(recommendation, language)

    except Exception as e:
        error_msg = f"Error in assess_hiv_risk: {e}"
        print(error_msg)
        if hasattr(websocket, 'teachability'):
            error_memo = (
                "=== HIV Risk Assessment Error ===\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Error: {error_msg}\n"
                "Partial Results:\n" + "\n\n".join(assessment_log if 'assessment_log' in locals() else ["No responses recorded"])
            )
            websocket.teachability._consider_memo_storage(error_memo)
        await websocket.send_text("Sorry, there was an error processing your responses.")



# FUNCTION TO SEARCH FOR NEAREST PROVIDER
def search_provider(zip_code: str, language: str) -> Dict:
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
            time.sleep(5)  

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
            
            time.sleep(5)  
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            results = soup.find_all('div', class_='locator-results-item')
            
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

            df = pd.DataFrame(extracted_data)
            df['Distance'] = df['Distance'].str.replace(r'[^\d.]+', '', regex=True)
            df['Distance'] = pd.to_numeric(df['Distance'], errors='coerce')
            filtered_df = df[df['Distance'] <= 30].nsmallest(5, 'Distance')  

            if filtered_df.empty:
                return "I couldn't find any providers within 30 miles of that ZIP code. Would you like to try a different ZIP code?"

            formatted_results = "Here are the 5 closest providers to you:\n\n"
            for _, provider in filtered_df.iterrows():
                formatted_results += f"{provider['Name']}\n"
                formatted_results += f"- Address: {provider['Address']}\n"
                formatted_results += f"- Phone: {provider['Phone']}\n"
                formatted_results += f"- Distance: {provider['Distance']} miles\n\n"
            
            formatted_results += "Would you like any additional information about these providers?"
            
            return translate_question(formatted_results, language)

        except Exception as e:
            print(f"Error during search: {str(e)}")
            print("Page source:", driver.page_source)  
            raise
            
    except Exception as e:
        print(f"Error in search_provider: {str(e)}")
        return translate_question(f"I'm sorry, I couldn't find any providers near you. Technical Error: {str(e)}", language)
    
    finally:
        if 'driver' in locals():
            print("Closing Chrome driver...")
            driver.quit()

async def assess_ttm_stage_single_question(websocket: WebSocket, language: str) -> str:
    question = """Of course, I will ask you a single question to assess your status of change. 
Are you currently engaging in Prep uptake on a regular basis? Please respond with the number corresponding to your answer: 
1. No, and I do not intend to start in the next 6 months.
2. No, but I intend to start in the next 6 months.
3. No, but I intend to start in the next 30 days.
4. Yes, I have been for less than 6 months.
5. Yes, I have been for more than 6 months."""

    await websocket.send_text(translate_question(question, language))
    
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
            return translate_question(f"Based on your response, you are in the '{stage}' stage of change regarding PrEP uptake. Let me explain what this means and discuss possible next steps.", language)
        else:
            return translate_question("I didn't catch your response. Please respond with a number from 1 to 5 corresponding to your situation.", language)
            
    except Exception as e:
        print(f"Error processing response: {e}")
        return translate_question("I'm having trouble processing your response. Please try again with a number from 1 to 5.", language)




def notify_research_assistant(support_type, assistant_email, client_id, smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465, user_contact_info: str = None):
    """
    Function to notify research assistant when a client needs personal support.
    
    Parameters:
    client_name (str): Name of the client
    client_id (str): ID of the client
    support_type (str): Type of support needed (e.g., emotional, financial, etc.)
    assistant_email (str): Email address of the research assistant
    """
    print(f"Notifying research assistant {assistant_email} for client (ID: {client_id}) with support type {support_type}.")
    
    # Set up email details
    sender_email = "t28184003@gmail.com"
    sender_password = "vnqs wulc clye ncjx"
    subject = f"Client (ID: {client_id}) Needs Personal Support"
    
    # Create the email content
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = assistant_email
    message["Subject"] = subject
    

    body = f"""
    Hello,

    The client (ID: {client_id}) requires personal support in the following area: {support_type}.
    Please reach out to the client using the following contact information:
    {user_contact_info}

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
        
    
        server.sendmail(sender_email, assistant_email, message.as_string())
        # Close the connection
        server.quit()
        print(f"Notification sent to {assistant_email} regarding client {client_id}.")
        
        return (f"A research assistant has been notified and will reach out to provide {support_type} support.")
    
    except Exception as e:
        print(f"Failed to send notification. Error: {e}")
        return (f"Failed to send notification. Error: {e}")
        

supabase = create_client(
    os.environ.get("NEXT_PUBLIC_SUPABASE_URL"),
    os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)

async def record_support_request(websocket: WebSocket, chat_id: str, language: str) -> str:
    """
    Record in Supabase when a user requests support.
    """
    try:
        # Step 1: Ask for support type
        await websocket.send_text(translate_question(
            "To help connect you with the right support:\n"
            "What type of support would be most helpful? (emotional, financial, medical support, etc.)",
            language
        ))
        print("Sent support type question.")

    
        try:
            response = await websocket.receive_text()
            print("Support type response:", response)
            response_json = json.loads(response)
            support_type = response_json.get("content", "")
        except json.JSONDecodeError:
            await websocket.send_text(translate_question("I didn't understand that. Could you please rephrase your response?", language))
            return "Invalid response format."

        # Step 2: Ask for contact preference and validate response
        while True:
            if 'formatted_contact_preference' not in locals():  # Only show full message first time
                formatted_contact_preference = "How would you like the research assistant to contact you?\n\n"
                formatted_contact_preference += "1: By phone.\n\n"
                formatted_contact_preference += "2: By email. \n\n"
                formatted_contact_preference += "0: I do not want to be contacted.\n\n"
                formatted_contact_preference += "Please reply with 0, 1, or 2."
                await websocket.send_text(translate_question(formatted_contact_preference, language))
            else:
                await websocket.send_text(translate_question("Please make sure to answer with 0, 1, or 2.", language))

            try:
                response = await websocket.receive_text()
                print("Contact preference response:", response)
                response_json = json.loads(response)
                contact_preference = response_json.get("content", "").strip()
                
                if contact_preference in ["0", "1", "2"]:
                    break
                else:
                    await websocket.send_text(translate_question("Please make sure to answer with 0, 1, or 2.", language))
            except json.JSONDecodeError:
                await websocket.send_text(translate_question("I didn't understand that. Please respond with 0, 1, or 2.", language)         )

        # If they don't want contact
        if contact_preference == "0":
            return "I understand you don't want to be contacted. Is there anything else I can help you with?"

        # Step 3: Get contact information based on preference
        if contact_preference == "1":
            contact_info_prompt = "Please provide your phone number so that a research assistant can reach out to you."
        else:  # contact_preference == "2"
            contact_info_prompt = "Please provide your email address so that a research assistant can reach out to you."
        await websocket.send_text(translate_question(contact_info_prompt, language))

        try:
            response = await websocket.receive_text()
            print("Contact info response:", response)
            response_json = json.loads(response)
            contact_info = response_json.get("content", "").strip()
        except json.JSONDecodeError:
            await websocket.send_text(translate_question("I didn't understand that. Could you please try again?", language))
            return "Invalid response format."

        # Record in Supabase
        supabase_record = {
            "client_name": "Anonymous",
            "support_type": support_type,
            "created_at": datetime.now().isoformat(),
            "notified": False,
            "chat_id": chat_id,
            "email": contact_info if contact_preference == "2" else None,
            "phone": contact_info if contact_preference == "1" else None
        }

        supabase.table("support_requests").insert(supabase_record).execute()

        if contact_preference == "1":
            contact_method = "phone"
        elif contact_preference == "2":
            contact_method = "email"
        else:
            contact_method = "Please answer with 0, 1, or 2."

        return translate_question(f"Thank you for sharing that. When your chat session ends, a research assistant will reach out to provide {support_type} support via {contact_method}. What else can I help you with?", language)


    except Exception as e:
        print(f"Error recording support request: {e}")
        return translate_question("I'm having trouble recording your request. Please let me know if you'd like to try again.", language)


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
            try:
        
                history_response = supabase.table("messages") \
                    .select('*') \
                    .eq("chat_id", chat_id) \
                    .execute()

                chat_history = [msg["role"] + ": " + msg["content"] for msg in history_response.data or []]

                if not chat_history:
                    print("No chat messages found.")
                    return None

                # Evaluate chat history accuracy
                evaluate_counseling_response(str(chat_id), chat_history)
                print(f"Evaluated {len(chat_history)} chat messages")

                # Evaluate chat history motivational interviewing
                evaluate_motivational_interview(str(chat_id), chat_history)
                print(f"Evaluated {len(chat_history)} chat messages")

                # Mark chats as evaluated
                supabase.table("chats") \
                    .update({"chat_evaluation_sent": True}) \
                    .in_("id", chat_ids) \
                    .execute()

            except Exception as e:
                print(f"Error processing chat {chat_id}: {e}")
                continue

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
                
                user_contact_info = request['email'] if request['email'] else request['phone']
                notify_research_assistant(request['support_type'], "jun_tao@brown.edu", client_id, user_contact_info = user_contact_info)
                supabase.table("support_requests")\
                    .update({"notified": True})\
                    .eq("id", request_id)\
                    .execute()
                print(f"Support request {request_id} updated successfully.")
        else:
            print("No support requests need updating.")

    except Exception as e:
        print(f"An error occurred: {e}")


async def create_transcript():
    try:
        non_transcribed_chats = supabase.table("messages") \
            .select("chat_id") \
            .is_("has_transcript", False) \
            .execute()

        chat_ids = list(set(msg["chat_id"] for msg in non_transcribed_chats.data or []))
        
        if not chat_ids:
            print("No chats without transcripts found.")
            return "No chats need transcripts"

        for chat_id in chat_ids:
            # Check chat activity status
            chat_response = supabase.table("chats")\
                .select("updated_at", "created_at")\
                .eq("id", chat_id.strip())\
                .execute()
            
            updated_at_str = chat_response.data[0]['updated_at']
            if not updated_at_str:
                updated_at_str = chat_response.data[0]['created_at']
            if not updated_at_str:
                print(f"No timestamp found for chat_id: {chat_id}")
                continue
                
            # Convert to datetime and check inactivity
            updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            # Only proceed if chat has been inactive for more than 5 minutes
            if (current_time - updated_at).total_seconds() <= 300:
                print(f"Chat {chat_id} is still active, skipping")
                continue

            # Fetch chat history with ordering
            chat_history = supabase.table("messages")\
                .select("*")\
                .eq("chat_id", chat_id)\
                .is_("has_transcript", False)\
                .order("created_at", desc=False)\
                .execute()
            
            if not chat_history.data:
                print(f"No messages found for chat {chat_id}")
                continue

            # Create transcript
            transcript = ""
            user_id = None
            for message in chat_history.data:
                role = message["role"]
                content = message["content"]
                created_at = message.get("created_at", "")  # Optionally add timestamp
                if user_id is None:
                    user_id = message["user_id"]
                transcript += f"{role}: {content}\n"  # Added timestamp to transcript
            
            transcript_data = {
                "user_id": user_id,
                "chat_id": chat_id,
                "messages": transcript
            }
            
            # Move this try-except block inside the chat_id loop
            try:
                transcript_chat_ids = [chat["chat_id"] for chat in supabase.table("transcripts").select("chat_id").execute().data or []]
                if chat_id in transcript_chat_ids:
                    update_response = supabase.table("messages")\
                            .update({"has_transcript": True})\
                            .eq("id", message['id'])\
                            .execute()
                    print(f"Updated message {message['id']}: {update_response.data}")
                    print("Chat already has a transcript, skipping")

                    verify = supabase.table("messages") \
                    .select("id, has_transcript") \
                    .eq("chat_id", chat_id) \
                    .execute()
                    
                    continue
                before_state = supabase.table("messages")\
                    .select("id, chat_id, has_transcript")\
                    .eq("chat_id", chat_id)\
                    .execute()
               
                transcript_response = supabase.table("transcripts")\
                    .insert(transcript_data)\
                    .execute()
        
                if transcript_response.data:
                    # Modified update query to be more explicit
                    for message in before_state.data:
                        update_response = supabase.table("messages")\
                            .update({"has_transcript": True})\
                            .eq("id", message['id'])\
                            .execute()
                        print(f"Updated message {message['id']}: {update_response.data}")
                    
                   
                   
            except Exception as e:
                print(f"Error processing chat 2 {chat_id}: {e}")
                continue

    except Exception as e:
        print(f"Error in create_transcript: {e}")
        return "Error creating transcripts"

    return "Transcripts created successfully"


                