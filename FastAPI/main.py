# FastAPI part
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor, TrackableGroupChatManager
from collections.abc import Mapping
import json

app = FastAPI()


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
            response = workflow_manager.get_latest_response() 

            # Send the latest response to the frontend
            if response is not None:  # Check for None explicitly
                if isinstance(response, Mapping):
                    # Convert the dict to a JSON string
                    message = json.dumps(response)
                    await websocket.send_text(message)  # Send the JSON message via WebSocket
                elif isinstance(response, (str, bytes, bytearray, memoryview)):
                    await websocket.send_text(response)  # Send directly if it's a string or similar type
                else:
                    raise TypeError(f"Unsupported message type: {type(response)}")
            else:
                print("Response is None; nothing to send.")

            # # Retrieve the entire chat history (including counselor's responses)
            # chat_history = workflow_manager.get_history()
            
            # # Send the chat history to the frontend (if needed)
            # for message in chat_history:
            #     if message['sender'] != 'patient':
            #         formatted_message = f"{message['sender']} to {message['receiver']}: {message['message']}"
            #         await websocket.send_text(formatted_message)


                

        except WebSocketDisconnect:
            print("Client disconnected")
            break
        except Exception as e:
            print(f"Connection error: {e}")
