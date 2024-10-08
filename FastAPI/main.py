from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import asyncio
from CHIA.CHIA_LangchainEmbeddings import WorkflowManager

app = FastAPI()
workflow_manager = WorkflowManager()

class Message(BaseModel):
    user_id: str
    message: str

@app.post("/send_message/")
async def send_message(message: Message):
    response = await workflow_manager.get_response(message.message)
    return {"response": response}

@app.get("/history/{user_id}")
def get_history(user_id: str):
    # Optionally, filter history by user_id if needed
    return {"history": workflow_manager.get_history()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    counselor = WorkflowManager()
    
    # Send the initial greeting to the frontend
    initial_message = "How can I help you?"
    await websocket.send_text(initial_message)

    while True:
        try:
            # Receive message from the front end
            data = await websocket.receive_text()
            print(f"Received message: {data}")

            # Process the message using the chatbot logic
            response = await counselor.get_response(data)

            # Send the counselor's response back to the front end
            await websocket.send_text(response)

        except Exception as e:
            print(f"Connection closed: {e}")
            break

