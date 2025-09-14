import asyncio
import json
import uuid
import time
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import sys
from typing import Any, Dict, List, Optional


# This assumes automate_transcripts.py is in FastAPI/agents/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

#
try:
    from FastAPI.CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor
except ImportError:
    print("Error: Could not import HIVPrEPCounselor. Ensure structure and sys.path are correct.")
    sys.exit(1)

load_dotenv()

USER_ID = f"direct_llm_user_{uuid.uuid4()}"
CHAT_ID = str(uuid.uuid4())
TEACHABILITY_ENABLED = False
TARGET_MESSAGE_COUNT = 15 

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = "gpt-3.5-turbo"

FIRST_USER_MESSAGE_CONTENT = "Hello, I have some questions about HIV and PrEP."

# --- Mock WebSocket ---
class MockWebSocket:
    """Simulates WebSocket for direct interaction with HIVPrEPCounselor."""
    def __init__(self):
        self.sent_messages = []
        self.receive_queue = asyncio.Queue()
        self.accepted = False
        self.closed = False
        # Store the LLM response function to generate replies needed by receive_text
        self._llm_responder = None

    async def accept(self):
        print("[MockWebSocket] Accepting connection.")
        self.accepted = True

    async def send_text(self, text: str):
        print(f"[MockWebSocket] CHIA trying to send: {text}")
        self.sent_messages.append({"type": "text", "content": text})
 
    async def send_json(self, data: dict):
        print(f"[MockWebSocket] CHIA trying to send JSON: {json.dumps(data)}")
        self.sent_messages.append({"type": "json", "content": data})
        if data.get("type") == "teachability_flag":
             print("[MockWebSocket] Received teachability flag confirmation.")

    async def receive_text(self) -> str:
        """Waits for the next simulated user message."""
        if self.closed:
            raise Exception("WebSocket is closed") # Or appropriate WebSocket exception
        print("[MockWebSocket] Waiting for user input (receive_text)...")
        # A function call (like assess_hiv_risk) might call this expecting user input.
        # The main loop needs to anticipate this and put the LLM's response into the queue.
        user_response = await self.receive_queue.get()
        print(f"[MockWebSocket] Received user input: {user_response}")
        self.receive_queue.task_done()
        # Wrap in JSON like the frontend might
        return json.dumps({"type": "message", "content": user_response, "messageId": f"mock_recv_{uuid.uuid4()}"})


    async def close(self, code: int = 1000):
        print(f"[MockWebSocket] Closing connection with code {code}.")
        self.closed = True

    # Method for the main loop to inject the next user response
    async def inject_user_response(self, text: str):
        await self.receive_queue.put(text)

# --- LLM Generation (similar to previous version) ---
def sanitize_for_llm(text: str) -> str:
    # ... (keep sanitize_for_llm function from previous example) ...
    if not isinstance(text, str): return ""
    import re
    text = re.sub(r"^(assistant|chia|counselor|bot):\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^(user|patient|me):\s*", "", text, flags=re.IGNORECASE).strip()
    return text

async def generate_llm_response(conversation_history):
    clean_history_for_llm = []
    last_role = None
    for msg in conversation_history:
        role = msg.get("role")
        content = msg.get("content")
        if role in ["user", "assistant"] and isinstance(content, str) and content.strip():
            if role != last_role:
                sanitized_content = sanitize_for_llm(content)
                if sanitized_content:
                    clean_history_for_llm.append({"role": role, "content": sanitized_content})
                    last_role = role

    prompt_messages = [
        {"role": "system", "content": (
            "You are simulating a HUMAN user asking questions to an HIV/PrEP counseling chatbot named CHIA. Act as a patient seeking information, not a counselor. "
            "The patient should never say things such as 'I am here to help you', 'I am here to assist you', or 'I am here to support you'. "
            "Your persona is someone seeking information. Ask relevant questions, react naturally to CHIA's responses based on the dialogue history. "
            "Respond concisely like a real chat user. Provide simple answers ('yes', 'no', 'maybe', 'I don't know') if CHIA asks assessment questions. "
            "Focus ONLY on being the USER. NEVER act as the assistant or CHIA. "
            "NEVER start your response with 'CHIA:' or 'Assistant:'. Keep responses brief. "
            "If the conversation seems stuck or CHIA gives errors, ask a clarifying question or try a different topic."
            "The dialogue history follows."
        )}
    ]
    prompt_messages.extend(clean_history_for_llm)

    try:
        completion = await client.chat.completions.create(
            model=LLM_MODEL, messages=prompt_messages, temperature=0.75, max_tokens=80
        )
        response_content = completion.choices[0].message.content.strip()
        sanitized_response = sanitize_for_llm(response_content)
        if not sanitized_response: return "Okay, please continue."
        return sanitized_response
    except Exception as e:
        print(f"!!! Error calling OpenAI API: {e}")
        return "Okay, thank you anyway."

# --- Main Simulation ---
async def run_direct_simulation():
    """Instantiates counselor and runs LLM-driven chat directly."""
    print("--- Starting Direct Simulation ---")
    print(f"Simulating User ID: {USER_ID}, Chat ID: {CHAT_ID}")

    # 1. Create Mock WebSocket and Counselor Instance
    mock_ws = MockWebSocket()
    # Need to call accept manually if counselor's init expects it
    await mock_ws.accept()

    try:
        # Pass the mock websocket to the counselor
        workflow_manager = HIVPrEPCounselor(
            websocket=mock_ws, # Use the mock object
            user_id=USER_ID,
            chat_id=CHAT_ID,
            teachability_flag=TEACHABILITY_ENABLED # Set based on config
        )
        # Manually trigger teachability state send if needed by logic
        # await workflow_manager.send_teachability_state()
    except Exception as e:
        print(f"!!! Error initializing HIVPrEPCounselor: {e}")
        import traceback
        traceback.print_exc()
        return

    llm_conversation_history = [] # History for LLM prompt
    transcript_log = [] # Full log for file
    chat_message_count = 0

    # 2. Initial User Message
    current_user_message_content = sanitize_for_llm(FIRST_USER_MESSAGE_CONTENT)
    print(f"\n>>> Simulating User: {current_user_message_content}")
    transcript_log.append(f"User: {current_user_message_content}")
    llm_conversation_history.append({"role": "user", "content": current_user_message_content})
    chat_message_count += 1

    # 3. Conversation Loop
    while chat_message_count < TARGET_MESSAGE_COUNT:
        print(f"\n--- Chat Messages: {chat_message_count}/{TARGET_MESSAGE_COUNT} ---")

        # 3a. Inject the user's message content IF a function might need it via receive_text
        # This is speculative - depends on whether initiate_chat might trigger
        # functions that call receive_text immediately. For simple Q&A it might not.
        # await mock_ws.inject_user_response(current_user_message_content) # <-- This might be needed if functions call receive_text

        # 3b. Call initiate_chat with the user's message content
        try:
            # initiate_chat should trigger the agent workflow
            print(f"--- Calling initiate_chat with: '{current_user_message_content}' ---")
            # Run initiate_chat and potentially triggered functions concurrently
            # If initiate_chat calls functions that await mock_ws.receive_text(),
            # the inject_user_response above needs to happen *before* or concurrently.
            # This interaction is the most complex part of the mock.
            # Let's try running initiate_chat and see if it blocks or runs.
            initiate_task = asyncio.create_task(
                 workflow_manager.initiate_chat(current_user_message_content)
            )

            # Wait for initiate_chat task to complete OR for a function inside it
            # to potentially call receive_text (which would block if queue is empty).
            # We might need a timeout here.
            await asyncio.wait_for(initiate_task, timeout=45.0) # Timeout for agent processing

            print("--- initiate_chat call finished ---")

        except asyncio.TimeoutError:
             print("!!! Timeout waiting for initiate_chat to complete.")
             transcript_log.append("CHIA: [Processing Timeout]")
             break
        except Exception as e:
            print(f"!!! Error during initiate_chat: {e}")
            import traceback
            traceback.print_exc()
            transcript_log.append(f"CHIA: [Error: {e}]")
            break # Stop simulation on error

        # 3c. Get the response from the counselor's state
        # Give agents a moment to update state if needed
        await asyncio.sleep(0.5)
        chia_response_content_raw = workflow_manager.get_latest_response()
        print(f"--- Got raw response from get_latest_response: '{chia_response_content_raw}' ---")

        if chia_response_content_raw:
            chat_message_count += 1
            chia_response_content_clean = sanitize_for_llm(chia_response_content_raw)

            if chia_response_content_clean:
                print(f"<<< CHIA Response (Clean): {chia_response_content_clean}")
                transcript_log.append(f"CHIA: {chia_response_content_clean}")
                llm_conversation_history.append({"role": "assistant", "content": chia_response_content_clean})
                if "goodbye" in chia_response_content_clean.lower(): break
            else:
                print(f"Warning: CHIA raw response invalid after sanitizing: '{chia_response_content_raw}'")
                transcript_log.append(f"CHIA (Invalid Content): {chia_response_content_raw}")
                # Decide whether to break or try generating a user response anyway
                # break
        else:
            # No response generated by get_latest_response
            print("!!! No response retrieved from CHIA.")
            # Don't increment chat_message_count if no response
            # Decide how to handle this - maybe try generating user response? Or break?
            transcript_log.append("CHIA: [No Response Found]")
            # Let's try to continue by generating a user prompt anyway
            # break

        # Check count before generating next user message
        if chat_message_count >= TARGET_MESSAGE_COUNT: break

        # 3d. Generate next user message using LLM
        next_user_content_raw = await generate_llm_response(llm_conversation_history)
        current_user_message_content = sanitize_for_llm(next_user_content_raw) # Prepare for next loop

        if not current_user_message_content:
            print("!!! LLM returned empty/invalid response. Ending.")
            transcript_log.append("User (LLM - Invalid): [Empty Response]")
            break

        print(f"\n>>> Simulating User: {current_user_message_content}")
        transcript_log.append(f"User (LLM): {current_user_message_content}")
        llm_conversation_history.append({"role": "user", "content": current_user_message_content})
        chat_message_count += 1

    # 4. End Simulation
    print(f"\n--- Simulation Complete (Total Chat Messages: {chat_message_count}) ---")
    await mock_ws.close() # Close the mock websocket

    # Save transcript
    transcript_filename = f"transcript_direct_{CHAT_ID}.txt"
    with open(transcript_filename, "w") as f: f.write("\n".join(transcript_log))
    print(f"Transcript saved to {transcript_filename}")


# Main execution block
if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set.")
    else:
        try:
            asyncio.run(run_direct_simulation())
        except KeyboardInterrupt:
            print("\nSimulation interrupted.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()

    