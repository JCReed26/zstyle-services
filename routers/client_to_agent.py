from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio 
import os 
from dotenv import load_dotenv

import logging
from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler

logging_client = Client()
handler = CloudLoggingHandler(logging_client)
logger = logging.getLogger("agent-connect-server.client_to_agent")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

load_dotenv()

#AGENT_URL = "ws://localhost:3000/" # Local Agent WebSocket URL
AGENT_URL = os.getenv("AGENT_URL") # GCP Secret WebSocket URL

if not AGENT_URL:
    raise RuntimeError("AGENT_URL environment variable is not set.")

router = APIRouter(prefix="/agent")

class WebsocketHandler: 
    def __init__(self, user_id: str, is_audio: str, remote_url: str, client_ws: WebSocket):
        self.user_id = user_id
        self.is_audio = is_audio
        self.remote_url = remote_url
        self.client_ws = client_ws
        self.remote_ws = None

    async def connect(self): 
        await self.client_ws.accept()
        async with websockets.connect(self.remote_url) as self.remote_ws:
            await asyncio.gather(
                self._client_to_remote(),
                self._remote_to_client()
            )

    async def _client_to_remote(self):
        try:
            while True:
                msg = await self.client_ws.receive()
                if "text" in msg and msg["text"] is not None:
                    await self.remote_ws.send(msg["text"])
                if "bytes" in msg and msg["bytes"] is not None: 
                    await self.remote_ws.send(msg["bytes"])
        except WebSocketDisconnect:
            await self.remote_ws.close()
        except Exception:
            await self.remote_ws.close()

    # DOUBTS: I have doubts that the is_instance will be compatible with ADK like this 
    async def _remote_to_client(self):
        try:
            while True: 
                async for msg in self.remote_ws:
                    if isinstance(msg, str):
                        await self.client_ws.send_text(msg)
                    else:
                        await self.client_ws.send_bytes(msg)
        except Exception:
            await self.client_ws.close()

# All UIs will connect through this proxy websocket 
@router.websocket("/ws-proxy/{user_id}")
async def websocket_proxy(websocket: WebSocket, user_id: str, is_audio: str):
    # Need to build the url here from 
    logger.info(f"User {user_id} is connecting ...")
    if AGENT_URL is None:
        raise ValueError("AGENT_URL environment variable is not set. Please ensure it is configured.")
    final_url = f"wss://{AGENT_URL}/ws/{user_id}?is_audio={is_audio}"
    logger.debug(f"DEBUG: final agent url: {final_url} begin connection")
    websocket_proxy = WebsocketHandler(user_id, is_audio, final_url, websocket)
    await websocket_proxy.connect()

# Here will be a websocket built for the telnyx phone
