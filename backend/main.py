from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import asyncio
import os
from dotenv import load_dotenv
from agents import HIVPrEPCounselor
from tools.functions import (
    check_inactive_chats,
    get_chat_history,
    create_transcript
)
from contextlib import asynccontextmanager
from datetime import datetime
import warnings

# Load environment variables
# Try loading from different possible locations
env_loaded = False
for env_path in ['.env', '../.env', './.env']:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        env_loaded = True
        break

if not env_loaded:
    print("Warning: No .env file found in expected locations")

# Ensure OPENAI_API_KEY is available for autogen
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment variables")
    print("Available environment variables with 'OPENAI' in name:")
    for key, value in os.environ.items():
        if 'OPENAI' in key.upper():
            print(f"  {key}: {value[:10] if value else 'EMPTY'}...")
    exit(1)

# Set up autogen configuration

# Suppress autogen API key validation warnings since we have a valid key
warnings.filterwarnings(
    "ignore",
    message=".*API key specified is not a valid OpenAI format.*"
)
warnings.filterwarnings(
    "ignore",
    message=".*The API key specified is not a valid OpenAI format.*"
)


# Ensure the environment variable is set for autogen
os.environ["OPENAI_API_KEY"] = api_key

# Create a proper config list for autogen to use by default
config_list = [
    {
        "model": "gpt-4o",
        "api_key": api_key
    }
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create task for checking inactive chats
    task = asyncio.create_task(run_inactive_chat_checker())
    yield
    # Shutdown: Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Background task cancelled")


async def run_inactive_chat_checker():
    counter = 0
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Running check #{counter} at {current_time}")

            await get_chat_history()
            await check_inactive_chats()
            await create_transcript()

            logger.info(f"Check #{counter} completed")
            counter += 1
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"Error in check #{counter}: {e}")
            await asyncio.sleep(60)  # Wait before retrying

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = None
    workflow_manager = None
    chat_id = None
    chat_id_received = False
    teachability_flag = None

    try:
        while True:
            data = await websocket.receive_text()

            parsed_data = json.loads(data)

            # Extract message fields
            message_type = parsed_data.get('type')
            content = parsed_data.get('content')
            message_id = parsed_data.get('messageId')

            if not message_type or not content:
                logger.warning(f"Invalid message received: {parsed_data}")
                continue

            if message_type == "teachability_flag":
                teachability_flag = content
                continue

            # Handle user_id message
            if message_type == "user_id":
                user_id = content
                workflow_manager = HIVPrEPCounselor(
                    websocket, user_id, chat_id, teachability_flag)
                continue

            if message_type == "chat_id":
                chat_id = content
                if chat_id_received:
                    continue
                workflow_manager = HIVPrEPCounselor(
                    websocket, user_id, chat_id, teachability_flag)
                chat_id_received = True
                continue

            if message_type == "message":
                # Check if message is within deduplication window
                try:
                    if "chat_id" in parsed_data:
                        continue
                    # Pass the content string, not the entire parsed_data
                    await workflow_manager.initiate_chat(content)
                    response = workflow_manager.get_latest_response()

                    if response:
                        await websocket.send_text(json.dumps({
                            "type": "chat_response",
                            "messageId": message_id,
                            "content": response
                        }))
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    error_message = ("I'm here to help. "
                                     "Could you please rephrase that?")
                    await websocket.send_text(json.dumps({
                        "type": "chat_response",
                        "messageId": message_id,
                        "content": error_message
                    }))

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {user_id}")
    except Exception as e:
        logger.error(f"Connection error: {e}")
