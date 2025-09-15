"""
Chat management tools for handling chat history, transcripts, and inactivity.
"""
from supabase import create_client
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv("../.env")

# Initialize Supabase client
supabase = create_client(
    os.getenv("NEXT_PUBLIC_SUPABASE_URL"),
    os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
)


async def handle_inactivity(user_id, last_activity_time):
    """
    Handle the case where the user has been inactive for more than 5 minutes.
    This could involve sending an email or logging the event.
    """
    print(f"User {user_id} has been inactive since {last_activity_time}. "
          f"Triggering action.")
    
    # Implement your logic to send the email or take the necessary action
    # For example, call your email service here
    # email_service.send_inactivity_email(user_id)

    # Example log:
    print(f"Sending email notification to user {user_id} about inactivity "
          f"since {last_activity_time}")


async def get_chat_history():
    """Get and evaluate chat history for non-evaluated chats."""
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
        print("chat_ids", chat_ids[0])

        for chat_id in chat_ids:
            
            try:
        
                history_response = supabase.table("messages") \
                    .select('*') \
                    .eq("chat_id", chat_id) \
                    .execute()

                chat_history = [msg["role"] + ": " + msg["content"] 
                               for msg in history_response.data or []]

                if not chat_history:
                    print("No chat messages found.")
                    return None

                # Evaluate chat history accuracy
                # evaluate_counseling_response(str(chat_id), chat_history)  # Function not available
                print(f"Evaluated {len(chat_history)} chat messages")

                # # Evaluate chat history motivational interviewing
                # evaluate_motivational_interview(str(chat_id), chat_history)
                # print(f"Evaluated {len(chat_history)} chat messages")

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


async def create_transcript():
    """Create transcripts for inactive chats."""
    try:
        non_transcribed_chats = supabase.table("messages") \
            .select("chat_id") \
            .is_("has_transcript", False) \
            .execute()

        chat_ids = list(set(msg["chat_id"]
                            for msg in non_transcribed_chats.data or []))
        
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
                # created_at = message.get("created_at", "")  # Optionally add timestamp
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
                transcript_chat_ids = [chat["chat_id"]
                                       for chat in supabase.table("transcripts")
                                       .select("chat_id").execute().data or []]
                if chat_id in transcript_chat_ids:
                    update_response = supabase.table("messages")\
                            .update({"has_transcript": True})\
                            .eq("id", message['id'])\
                            .execute()
                    print(f"Updated message {message['id']}: "
                          f"{update_response.data}")
                    print("Chat already has a transcript, skipping")

                    # verify = supabase.table("messages") \
                    #     .select("id, has_transcript") \
                    #     .eq("chat_id", chat_id) \
                    #     .execute()
                    
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
                        print(f"Updated message {message['id']}: "
                              f"{update_response.data}")

            except Exception as e:
                print(f"Error processing chat 2 {chat_id}: {e}")
                continue

    except Exception as e:
        print(f"Error in create_transcript: {e}")
        return "Error creating transcripts"

    return "Transcripts created successfully"
