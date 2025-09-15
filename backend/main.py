from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import sys
from pathlib import Path

# Add the modified packages to the path to override the installed autogen
backend_dir = Path(__file__).parent
modified_packages_dir = backend_dir / "modified_packages"
sys.path.insert(0, str(modified_packages_dir))

try:
    # Try absolute import first (when running from project root)
    from backend.services.counselor_session import HIVPrEPCounselor  # noqa: E402
except ImportError:
    # Fall back to relative import (when running from backend directory)
    from services.counselor_session import HIVPrEPCounselor  # noqa: E402
from startup import lifespan  # noqa: E402
from config import settings  # noqa: E402

# Set up logging
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
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
                # Only create workflow_manager if we don't have one yet
                if workflow_manager is None:
                    workflow_manager = HIVPrEPCounselor(
                        websocket, user_id, chat_id, teachability_flag)
                continue

            if message_type == "chat_id":
                chat_id = content
                if chat_id_received:
                    continue
                # Only create workflow_manager if we don't have one yet
                if workflow_manager is None:
                    workflow_manager = HIVPrEPCounselor(
                        websocket, user_id, chat_id, teachability_flag)
                chat_id_received = True
                continue

            if message_type == "message":
                # Check if message is within deduplication window
                try:
                    if "chat_id" in parsed_data:
                        continue
                    # Pass the content string
                    # The GroupChatManager will handle WebSocket communication
                    await workflow_manager.initiate_chat(content)
                    print("Chat processing completed - "
                          "GroupChatManager handled WebSocket")
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
