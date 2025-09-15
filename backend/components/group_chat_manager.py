"""
TrackableGroupChatManager for handling WebSocket communication with frontend.
"""
import autogen
from typing import Optional


class TrackableGroupChatManager(autogen.GroupChatManager):
    """Enhanced GroupChatManager with WebSocket support and deduplication."""

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
                # Format the message according to frontend expectations
                import json
                response_data = {
                    "type": "chat_response",
                    "messageId": "counselor_response",
                    "content": message
                }
                json_message = json.dumps(response_data)

                await self.websocket.send_text(json_message)
                self._last_message = message
                print("WebSocket response sent successfully")
            except Exception as e:
                print(f"Error sending message: {e}")

    def _process_received_message(self, message, sender, silent):
        """Process and deduplicate messages."""
        # Don't send individual messages to WebSocket during conversation
        # The GroupChatManager will handle WebSocket communication at the end
        return super()._process_received_message(message, sender, silent)

    def set_counselor_name(self, counselor_name: str):
        """Set the counselor agent name for filtering responses."""
        self._counselor_name = counselor_name

    async def a_run_chat(self, messages=None, sender=None, config=None):
        """Override async run_chat to handle WebSocket communication."""
        # Call the parent's a_run_chat method to handle the conversation
        result = await super().a_run_chat(messages, sender, config)

        # After the conversation is complete, send the final response via
        # WebSocket
        if self.websocket and self._groupchat.messages:
            await self._send_final_response()

        return result

    async def _send_final_response(self):
        """Send the final counselor response to the WebSocket."""
        if not self.websocket:
            return

        counselor_name = getattr(self, '_counselor_name', None)
        if not counselor_name:
            return

        # Find the last message from the counselor
        for message in reversed(self._groupchat.messages):
            if (isinstance(message, dict) and
                    message.get('name') == counselor_name and
                    message.get('content')):
                formatted_message = self._clean_message(message['content'])
                if formatted_message:
                    await self.send_message(formatted_message)
                break
