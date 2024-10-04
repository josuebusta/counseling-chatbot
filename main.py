# main.py

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from CHIA.CHIA_LangchainEmbeddings import HIVPrEPCounselor
from queue import Queue
from threading import Thread
import asyncio
import logging

app = FastAPI()
queue = Queue()
counselor = None  # Will be initialized in the startup event

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency Injection Function
def get_counselor() -> HIVPrEPCounselor:
    if counselor is None:
        raise RuntimeError("Counselor not initialized.")
    return counselor

# WebSocket endpoint for real-time interactions
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, counselor: HIVPrEPCounselor = Depends(get_counselor)):
    await websocket.accept()
    logger.info("WebSocket connection accepted.")
    try:
        while True:
            # Wait for a message from the WebSocket client
            user_query = await websocket.receive_text()
            logger.info(f"Received WebSocket query: {user_query}")
            response = counselor.run(user_query)  # Process the user query
            await websocket.send_text(response)    # Send back the response
            logger.info(f"Sent WebSocket response: {response}")
    except Exception as e:
        error_message = f"Error: {str(e)}"
        await websocket.send_text(error_message)
        logger.error(f"WebSocket error: {e}")

# HTTP POST endpoint for handling queries
@app.post("/query")
async def handle_query(user_query: str, counselor: HIVPrEPCounselor = Depends(get_counselor)):
    try:
        logger.info(f"Received POST query: {user_query}")
        response = counselor.run(user_query)
        logger.info(f"Sending POST response: {response}")
        return {"response": response}
    except Exception as e:
        logger.error(f"Error handling query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Optional: Background function for any asynchronous work
def agent_interaction_workflow(queue: Queue):
    # Placeholder for agent interaction logic
    # Example: Interact with agents and put messages in the queue
    while True:
        # Simulate interaction
        message = "Agent message example."
        queue.put(message)
        asyncio.sleep(5)  # Replace with actual logic

@app.on_event("startup")
async def startup_event():
    global counselor
    try:
        # Initialize HIVPrEPCounselor here to avoid blocking the main thread
        counselor = HIVPrEPCounselor()
        logger.info("HIVPrEPCounselor initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize HIVPrEPCounselor: {e}")
        raise e  # Optionally, re-raise to prevent server from starting

    # Start any necessary background threads
    thread = Thread(target=agent_interaction_workflow, args=(queue,), daemon=True)
    thread.start()
    logger.info("Background agent interaction thread started.")

@app.on_event("shutdown")
async def shutdown_event():
    # Perform any necessary cleanup here
    logger.info("Shutting down application.")
