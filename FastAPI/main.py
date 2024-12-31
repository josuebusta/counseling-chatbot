# FastAPI part
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor, TrackableGroupChatManager
from collections.abc import Mapping
import json
from fastapi.middleware.cors import CORSMiddleware


from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import json
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self._active_connections: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self.user_id = None

    async def connect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            # Check if user already has an active connection
            if user_id in self._active_connections:
                existing_conn = self._active_connections[user_id]
                if existing_conn["websocket"] == websocket:
                    # Same websocket, just return
                    return
                else:
                    # Different websocket, close old one
                    try:
                        await existing_conn["websocket"].close()
                    except:
                        pass
                
            # Create new connection
            self._active_connections[user_id] = {
                "websocket": websocket,
                "workflow_manager": None,
                "initialized": False
            }
            
            logger.info(f"Client connected: {user_id}")
            # await websocket.send_text(json.dumps({
            #     "type": "connection_established",
            #     "content": "WebSocket connection established"
            # }))

    def set_initialized(self, user_id: str, workflow_manager):
        if user_id in self._active_connections:
            self._active_connections[user_id]["workflow_manager"] = workflow_manager
            self._active_connections[user_id]["initialized"] = True

            logger.info(f"Initialized workflow manager for user: {user_id}")

    def is_initialized(self, user_id: str) -> bool:
        return self._active_connections.get(user_id, {}).get("initialized", False)

    async def disconnect(self, user_id: str):
        async with self._lock:
            if user_id in self._active_connections:
                del self._active_connections[user_id]
                logger.info(f"Client disconnected: {user_id}")

    def get_connection(self, user_id: str) -> Optional[Dict]:
        return self._active_connections.get(user_id)
    
    def set_user_id(self, user_id: str):
        self.user_id = user_id
    
    def get_user_id(self) -> Optional[str]:
        return self.user_id

app = FastAPI()
manager = ConnectionManager()

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
    connection_initialized = False
    
    try:
        while True:
            data = await websocket.receive_text()
            parsed_data = json.loads(data)
            await websocket.send_text("Heyo")
            print("sent")
            print(f"parsed_data: {parsed_data}")
            
            
            message_type = parsed_data.get('type')
            content = parsed_data.get('content')
            message_id = parsed_data.get('messageId')
            
            # First message must be user_id
            if not connection_initialized:
                if message_type != "user_id":
                    # await websocket.send_text(json.dumps({
                    #     "type": "error",
                    #     "content": "First message must be user_id"
                    # }))
                
                    continue
                
                user_id = content
                if manager.is_initialized(user_id):
                    # Close existing connection if any
                    old_connection = manager.get_connection(user_id)
                    if old_connection:
                        try:
                            await old_connection["websocket"].close()
                        except:
                            pass
                
                await manager.connect(websocket, user_id)
                workflow_manager = HIVPrEPCounselor(websocket, user_id)
                manager.set_initialized(user_id, workflow_manager)
                connection_initialized = True
                
                # await websocket.send_text(json.dumps({
                #     "type": "connection_established",
                #     "content": "WebSocket connection established"
                # }))
                continue
            
            # Handle normal messages
            if message_type == "message":
                try:
                    connection = manager.get_connection(user_id)
                    workflow_manager = connection["workflow_manager"]
                    await workflow_manager.initiate_chat(content)
                    response = workflow_manager.get_latest_response()
                    
                    await websocket.send_text(json.dumps({
                        "type": "chat_response",
                        "messageId": message_id,
                        "content": response
                    }))
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    # await websocket.send_text(json.dumps({
                    #     "type": "error",
                    #     "messageId": message_id,
                    #     "content": f"Error processing message: {str(e)}"
                    # }))
    
    except WebSocketDisconnect:
        if user_id:
            await manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
        if user_id:
            await manager.disconnect(user_id)