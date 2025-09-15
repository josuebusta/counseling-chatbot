"""
TrackableGroupChatManager for handling WebSocket communication with the frontend.
"""
import asyncio
import autogen
from typing import Optional


class TrackableGroupChatManager(autogen.GroupChatManager):
    """Enhanced GroupChatManager with WebSocket support and message deduplication."""
    
    def __init__(self, websocket=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websocket = websocket
        self._last_message = None
        self._message_history = set()

    def _format_message(self, message, sender) -> Optional[str]:
        """Format the message for display, handling various message types."""
        try:
            if isinstance(message, dict):
                if 'function_call' in message or 'tool_calls' in message:
                    return None
                
                if 'content' in message and message['content']:
                    return self._clean_message(message['content'])
                
                if 'role' in message and message['role'] == 'tool':
                    if 'content' in message:
                        return self._clean_message(message['content'])
                    
            elif isinstance(message, str) and message.strip():
                return self._clean_message(message)
                
            return None
        except Exception as e:
            print(f"Error formatting message: {e}")
            return None

    def _clean_message(self, message: str) -> str:
        """Clean and format message content."""
        # Remove any existing prefixes
        prefixes = ["counselor:", "CHIA:", "assessment_bot:"]
        message = message.strip()

        for prefix in prefixes:
            if message.lower().startswith(prefix.lower()):
                message = message[len(prefix):].strip()
        return message

    async def send_message(self, message: str):
        """Send message to websocket, avoiding duplicates."""
        if message and message != self._last_message:
            try:
                await self.websocket.send_text(message)
                self._last_message = message
            except Exception as e:
                print(f"Error sending message: {e}")

    def _process_received_message(self, message, sender, silent):
        """Process and deduplicate messages."""
        if self.websocket:
            formatted_message = self._format_message(message, sender)
            if formatted_message:
                asyncio.create_task(self.send_message(formatted_message))

        return super()._process_received_message(message, sender, silent)
