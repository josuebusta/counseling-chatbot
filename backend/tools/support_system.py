"""
Support system tools for handling support requests and notifications.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from supabase import create_client
from datetime import datetime, timezone
from dotenv import load_dotenv
import os
from .utils import translate_question

load_dotenv("../.env")

# Initialize Supabase client
supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)


def notify_research_assistant(support_type, assistant_email, client_id,
                              smtp_server: str = "smtp.gmail.com",
                              smtp_port: int = 465,
                              user_contact_info: str = None):
    """
    Function to notify research assistant when a client needs personal support.
    
    Parameters:
    client_name (str): Name of the client
    client_id (str): ID of the client
    support_type (str): Type of support needed (e.g., emotional, financial, etc.)
    assistant_email (str): Email address of the research assistant
    """
    print(f"Notifying research assistant {assistant_email} for client "
          f"(ID: {client_id}) with support type {support_type}.")
    
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
        
        return (f"A research assistant has been notified and will reach out to "
                f"provide {support_type} support.")
    
    except Exception as e:
        print(f"Failed to send notification. Error: {e}")
        return (f"Failed to send notification. Error: {e}")


async def record_support_request(patient_agent, chat_id: str, language: str) -> str:
    """
    Record in Supabase when a user requests support.
    """
    try:
        # Step 1: Ask for support type
        response = await patient_agent.get_human_input(translate_question(
            "To help connect you with the right support:\n"
            "What type of support would be most helpful? "
            "(emotional, financial, medical support, etc.)",
            language
        ))
        print("Sent support type question.")

        try:
            print("Support type response:", response)
            response_json = json.loads(response)
            support_type = response_json.get("content", "")
        except json.JSONDecodeError:
            return translate_question(
                "I didn't understand that. Could you please rephrase your response?", 
                language)

        # Step 2: Ask for contact preference and validate response
        while True:
            if 'formatted_contact_preference' not in locals():  # Only show full message first time
                formatted_contact_preference = ("How would you like the research assistant "
                                                "to contact you?\n\n")
                formatted_contact_preference += "1: By phone.\n\n"
                formatted_contact_preference += "2: By email. \n\n"
                formatted_contact_preference += "0: I do not want to be contacted.\n\n"
                formatted_contact_preference += "Please reply with 0, 1, or 2."
                response = await patient_agent.get_human_input(translate_question(
                    formatted_contact_preference, language))
            else:
                response = await patient_agent.get_human_input(translate_question(
                    "Please make sure to answer with 0, 1, or 2.", language))

            try:
                print("Contact preference response:", response)
                response_json = json.loads(response)
                contact_preference = response_json.get("content", "").strip()
                
                if contact_preference in ["0", "1", "2"]:
                    break
                else:
                    # Continue loop to ask again
                    pass
            except json.JSONDecodeError:
                # Continue loop to ask again
                pass

        # If they don't want contact
        if contact_preference == "0":
            return ("I understand you don't want to be contacted. "
                    "Is there anything else I can help you with?")

        # Step 3: Get contact information based on preference
        if contact_preference == "1":
            contact_info_prompt = ("Please provide your phone number so that a "
                                  "research assistant can reach out to you.")
        else:  # contact_preference == "2"
            contact_info_prompt = ("Please provide your email address so that a "
                                  "research assistant can reach out to you.")
        response = await patient_agent.get_human_input(translate_question(contact_info_prompt,
                                                     language))

        try:
            print("Contact info response:", response)
            response_json = json.loads(response)
            contact_info = response_json.get("content", "").strip()
        except json.JSONDecodeError:
            return translate_question(
                "I didn't understand that. Could you please try again?", 
                language)

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

        return translate_question(f"Thank you for sharing that. When your chat session "
                                  f"ends, a research assistant will reach out to provide "
                                  f"{support_type} support via {contact_method}. What else "
                                  f"can I help you with?", language)


    except Exception as e:
        print(f"Error recording support request: {e}")
        return translate_question("I'm having trouble recording your request. "
                                  "Please let me know if you'd like to try again.",
                                  language)


async def check_inactive_chats():
    """Check for inactive chats and notify research assistants."""
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
                        
                        print(f"Adding request {request['id']} to updates - "
                              f"inactive for more than 5 minutes")

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
                notify_research_assistant(request['support_type'], 
                                         "jun_tao@brown.edu", client_id, 
                                         user_contact_info=user_contact_info)
                supabase.table("support_requests")\
                    .update({"notified": True})\
                    .eq("id", request_id)\
                    .execute()
                print(f"Support request {request_id} updated successfully.")
        else:
            print("No support requests need updating.")

    except Exception as e:
        print(f"An error occurred: {e}")
