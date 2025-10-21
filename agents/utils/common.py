import asyncio
import json 
import base64
import logging
import websockets 
import traceback 
from websockets.exceptions import ConnectionClosed

# logging for debug later
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


MODEL = "gemini-2.0-flash-live-preview"
VOICE_NAME = "Puck"

RECEIVE_SAMPLE_RATE = 24000
SEND_SAMPLE_RATE = 16000

SYSTEM_INSTRUCTION = """
You are a friendly and highly knowledgeable ______ agent for ______, specializing in _______.
Your goal is to _______________________________.
When a user asks a question about ______, you MUST _____.
Only answer the question if you know the answer. If you do not know I dont know for this.
"""

# Base Websocket server class for basics 
class BaseWebSocketServer:
    def __init__(self, host="0.0.0.0", port=4312):
        self.host = host
        self.port = port
        self.active_clients = {} # active websockets

    async def start(self):
        logger.info(f"starting websocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future() # runs forever 

    async def handle_client(self,websocket):
        """Handle new connection"""
        logger.info("Incoming WS %s", websocket.path)
        client_id = id(websocket)
        logger.info(f"New client Connected: {client_id}")

        await websocket.send(json.dumps({"type": "ready"}))

        try:
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            if client_id in self.active_clients:
                del self.active_clients[client_id]
    
    async def process_audio(self, websocket, client_id):
        """
        Process audio from the client. subclasses must implement
        """
        raise NotImplementedError("Subclasses must implement process_audio")