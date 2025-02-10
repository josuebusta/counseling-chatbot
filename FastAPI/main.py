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
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor
import hashlib
import time
from fastapi import BackgroundTasks
from CHIA.functions import check_inactive_chats, get_chat_history
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

            await get_chat_history()
            await check_inactive_chats()
            
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
    print("WebSocket connection established")
    user_id = None
    workflow_manager = None
    message_cache: Dict[str, float] = {}
    chat_id = None
    chat_id_received = False
    
    try:
        while True:
            data = await websocket.receive_text()

            parsed_data = json.loads(data)

            required_fields = ['type', 'content', 'messageId']
            if all(field in parsed_data for field in required_fields):
                message_type = parsed_data['type']
                content = parsed_data['content']
                message_id = parsed_data['messageId']
                print(f"Message Type: {message_type}, Content: {content}, Message ID: {message_id}")
            else:
                print("Invalid message received:", parsed_data)

            
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
                if chat_id_received:
                    continue
                workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
                chat_id_received = True
                continue
            
            if message_type == "user_id":
                user_id = content  
                if chat_id:
                    if chat_id_received:
                        continue
                    print("chat_id", chat_id)
                    workflow_manager = HIVPrEPCounselor(websocket, user_id, chat_id)
                    chat_id_received = True
                continue
            
         
            if message_type == "message":
           
                # Check if message is within deduplication window
                try:
                    if "chat_id" in parsed_data:
                        continue
                    print("parsed_data message", parsed_data)
                    await workflow_manager.initiate_chat(parsed_data)
                    # response = workflow_manager.get_latest_response()
                    # print("response", response)
                    
                    # if response:
                    #     await websocket.send_text(json.dumps({
                    #         "type": "chat_response",
                    #         "messageId": message_id,
                    #         "content": response
                    #     }))
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
    

