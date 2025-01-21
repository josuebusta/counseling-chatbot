from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
import logging
import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
import logging
import asyncio
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor, TrackableGroupChatManager
import hashlib
import time
from fastapi import BackgroundTasks
from CHIA.functions import check_inactive_chats
from contextlib import asynccontextmanager
from datetime import datetime

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
            
    
            
            await check_inactive_chats()
            
            logger.info(f"Check #{counter} completed")
            counter += 1
            await asyncio.sleep(300)  # 5 minutes
            
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
    message_cache: Dict[str, float] = {}
    chat_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            parsed_data = json.loads(data)
            print("parsed_data", parsed_data)
            message_type = parsed_data.get('type')
            print("message_type", message_type)
            content = parsed_data.get('content')
            print("content", content)
            message_id = parsed_data.get('messageId')
            print("message_id", message_id)
            
            # Handle user_id message
            if message_type == "user_id":
                user_id = content
                workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
                continue

            if message_type == "chat_id":
                chat_id = content
                workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
                continue
            
            if message_type == "user_id":
                user_id = content  
                if chat_id:
                    print("chat_id", chat_id)
                    workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
                continue
            
            # # Handle chat_id message
            # if message_type == "chat_id":
            #     chat_id = content
            #     print("chat_id", chat_id)
            #     # If user_id is already available, initialize workflow_manager
            #     if user_id:
            #         workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
            #     continue
            # Handle chat messages with deduplication
            if message_type == "message" and workflow_manager:
                # Create a unique hash for the message including a time window
                current_time = time.time()
                message_window = int(current_time / 5)  # 5-second window
                message_hash = hashlib.md5(f"{content}:{message_window}".encode()).hexdigest()
                
                # Check if message is within deduplication window
                if message_hash not in message_cache or \
                   (current_time - message_cache[message_hash]) >= 5.0:
                    
                    message_cache[message_hash] = current_time
                    try:
                        await workflow_manager.initiate_chat(content)
                        response = workflow_manager.get_latest_response()
                        
                        if response:
                            await websocket.send_text(json.dumps({
                                "type": "chat_response",
                                "messageId": message_id,
                                "content": response
                            }))
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "chat_response",
                            "messageId": message_id,
                            "content": "I'm here to help. Could you please rephrase that?"
                        }))
    
    except WebSocketDisconnect:
        print(f"Client disconnected: {user_id}")
    except Exception as e:
        print(f"Connection error: {e}")
    


