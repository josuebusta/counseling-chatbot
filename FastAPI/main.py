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


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

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
    
    try:
        while True:
            data = await websocket.receive_text()
            parsed_data = json.loads(data)
            
            message_type = parsed_data.get('type')
            content = parsed_data.get('content')
            message_id = parsed_data.get('messageId')
            
            # Handle user_id message
            if message_type == "user_id":
                user_id = content
                workflow_manager = HIVPrEPCounselor(websocket, user_id)
                continue
            
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
