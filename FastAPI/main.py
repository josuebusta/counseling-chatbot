# FastAPI part
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor, TrackableGroupChatManager

app = FastAPI()
# workflow_manager = HIVPrEPCounselor(websocket)

# class Message(BaseModel):
#     user_id: str
#     message: str

# @app.post("/send_message/")
# async def send_message(message: Message):
#     response = await workflow_manager.get_response(message.message)
#     return {"response": response}

# @app.get("/history/{user_id}")
# def get_history(user_id: str):
#     return {"history": workflow_manager.get_history()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    workflow_manager = HIVPrEPCounselor(websocket)

    # Set the WebSocket for the counselor
    workflow_manager.manager.websocket = websocket  # Pass the websocket to the manager

    # # Send initial greeting to the frontend
    # initial_message = "How can I help you?"
    # await websocket.send_text(initial_message)

    while True:
        try:
            # Receive message from the front end
            data = await websocket.receive_text()
            print(f"Received message: {data}")

            # Process the user input with the manager
            await workflow_manager.initiate_chat(data)

            # Optionally retrieve the latest chat response from the workflow manager
            response = workflow_manager.get_latest_response()  # Ensure this method exists in your manager

            # Send the latest response to the frontend
            if response:
                await websocket.send_text(response)

            # Retrieve the entire chat history (including counselor's responses)
            chat_history = workflow_manager.get_history()
            
            # Send the chat history to the frontend (if needed)
            for message in chat_history:
                formatted_message = f"{message['sender']} to {message['receiver']}: {message['message']}"
                await websocket.send_text(formatted_message)

        except WebSocketDisconnect:
            print("Client disconnected")
            break
        except Exception as e:
            print(f"Connection error: {e}")
