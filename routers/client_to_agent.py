"""
Enhanced WebSocket Proxy for Agent Connect Server
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio
import os
import json
from typing import Optional
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


""""From this point on I know what is happening but it is a different implementation than mine
    although mine worked locally when I deployed to cloudrun it did not I asked ai for help
    x-ai/grok-code-fast-1 to improve for the proxy of a bidi connection
    
    DEBUG HERE: AI mixed with human written code"""

# Connection timeouts and limits
CONNECTION_TIMEOUT = 60  # seconds
MESSAGE_TIMEOUT = 30     # seconds
MAX_CONNECTIONS_PER_USER = 3

class ConnectionManager:
    """Manages active WebSocket connections per user"""
    def __init__(self):
        self.active_connections: dict[str, set] = {}

    def add_connection(self, user_id: str, handler: 'WebsocketHandler'):
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(handler)

    def remove_connection(self, user_id: str, handler: 'WebsocketHandler'):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(handler)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    def get_user_connection_count(self, user_id: str) -> int:
        return len(self.active_connections.get(user_id, set()))

# Global connection manager
connection_manager = ConnectionManager()

class WebsocketHandler:
    def __init__(self, user_id: str, is_audio: str, remote_url: str, client_ws: WebSocket):
        self.user_id = user_id
        self.is_audio = is_audio
        self.remote_url = remote_url
        self.client_ws = client_ws
        self.remote_ws: Optional[websockets.WebSocketServerProtocol] = None
        self._running = True
        self._client_task: Optional[asyncio.Task] = None
        self._remote_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Main connection handler with proper cleanup"""
        try:
            # Check connection limits
            if connection_manager.get_user_connection_count(self.user_id) >= MAX_CONNECTIONS_PER_USER:
                await self.client_ws.accept()
                await self.client_ws.send_text(json.dumps({
                    "error": "Maximum connections exceeded for user"
                }))
                await self.client_ws.close()
                return

            await self.client_ws.accept()
            connection_manager.add_connection(self.user_id, self)

            logger.info(f"Accepted client connection for user {self.user_id}")

            # Connect to remote with timeout
            try:
                self.remote_ws = await asyncio.wait_for(
                    websockets.connect(
                        self.remote_url,
                        extra_headers={"User-Agent": "agent-connect-proxy/1.0"}
                    ),
                    timeout=CONNECTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout to remote for user {self.user_id}")
                await self.client_ws.send_text(json.dumps({
                    "error": "Connection timeout to agent service"
                }))
                return
            except Exception as e:
                logger.error(f"Failed to connect to remote for user {self.user_id}: {e}")
                await self.client_ws.send_text(json.dumps({
                    "error": f"Failed to connect to agent service: {str(e)}"
                }))
                return

            # Start bidirectional streaming tasks
            self._client_task = asyncio.create_task(self._client_to_remote())
            self._remote_task = asyncio.create_task(self._remote_to_client())

            # Wait for either task to complete (indicating connection should close)
            done, pending = await asyncio.wait(
                [self._client_task, self._remote_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Connection error for user {self.user_id}: {e}")
        finally:
            await self._cleanup()

    async def _client_to_remote(self):
        """Handle messages from client to remote agent"""
        try:
            while self._running and self.remote_ws:
                try:
                    # Receive with timeout
                    msg = await asyncio.wait_for(
                        self.client_ws.receive(),
                        timeout=MESSAGE_TIMEOUT
                    )

                    if msg["type"] == "websocket.disconnect":
                        logger.info(f"Client disconnected for user {self.user_id}")
                        break

                    # Handle text messages
                    if "text" in msg and msg["text"] is not None:
                        # Parse JSON message for proper ADK compatibility
                        try:
                            message_data = json.loads(msg["text"])

                            # Handle ping messages from client (keep-alive)
                            if message_data.get("type") == "ping":
                                await self.client_ws.send_text(json.dumps({"type": "pong"}))
                                continue

                            # Forward message to remote agent
                            await self.remote_ws.send(json.dumps(message_data))
                            logger.debug(f"Forwarded text message from user {self.user_id}")
                        except json.JSONDecodeError:
                            # If not JSON, send as plain text
                            await self.remote_ws.send(msg["text"])

                    # Handle binary messages
                    elif "bytes" in msg and msg["bytes"] is not None:
                        await self.remote_ws.send(msg["bytes"])
                        logger.debug(f"Forwarded binary message from user {self.user_id}")

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await self.client_ws.send_text(json.dumps({"type": "ping"}))
                    continue
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"Error in client-to-remote for user {self.user_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Client-to-remote task error for user {self.user_id}: {e}")
        finally:
            self._running = False

    async def _remote_to_client(self):
        """Handle messages from remote agent to client"""
        try:
            while self._running and self.remote_ws:
                try:
                    # Receive message with timeout
                    msg = await asyncio.wait_for(
                        self.remote_ws.recv(),
                        timeout=MESSAGE_TIMEOUT
                    )

                    # Handle different message types for ADK compatibility
                    if isinstance(msg, str):
                        # Try to parse as JSON first
                        try:
                            message_data = json.loads(msg)
                            await self.client_ws.send_text(json.dumps(message_data))
                        except json.JSONDecodeError:
                            # If not JSON, send as plain text
                            await self.client_ws.send_text(msg)
                    else:
                        # Binary message
                        await self.client_ws.send_bytes(msg)

                    logger.debug(f"Forwarded message to client for user {self.user_id}")

                except asyncio.TimeoutError:
                    # Connection is healthy, continue
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Remote connection closed for user {self.user_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in remote-to-client for user {self.user_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Remote-to-client task error for user {self.user_id}: {e}")
        finally:
            self._running = False

    async def _cleanup(self):
        """Clean up resources"""
        self._running = False

        # Remove from connection manager
        connection_manager.remove_connection(self.user_id, self)

        # Cancel tasks
        for task in [self._client_task, self._remote_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close connections
        for ws in [self.remote_ws, self.client_ws]:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

        logger.info(f"Cleaned up connection for user {self.user_id}")

# Health check endpoint for monitoring
@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring WebSocket proxy status"""
    return {
        "status": "healthy",
        "service": "websocket-proxy",
        "active_connections": sum(len(connections) for connections in connection_manager.active_connections.values()),
        "users_connected": len(connection_manager.active_connections)
    }

# Connection status endpoint
@router.get("/connections/{user_id}")
async def get_user_connections(user_id: str):
    """Get connection status for a specific user"""
    count = connection_manager.get_user_connection_count(user_id)
    return {
        "user_id": user_id,
        "active_connections": count,
        "max_connections": MAX_CONNECTIONS_PER_USER
    }

# All UIs will connect through this proxy websocket
@router.websocket("/ws-proxy/{user_id}")
async def websocket_proxy(websocket: WebSocket, user_id: str, is_audio: str):
    """Main WebSocket proxy endpoint with enhanced error handling"""
    try:
        logger.info(f"User {user_id} is connecting (audio: {is_audio})...")

        # Validate inputs
        if not user_id or len(user_id) > 100:  # Reasonable limit
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": "Invalid user_id"
            }))
            await websocket.close()
            return

        if is_audio not in ["true", "false"]:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": "Invalid is_audio parameter"
            }))
            await websocket.close()
            return

        if AGENT_URL is None:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": "AGENT_URL environment variable is not set"
            }))
            await websocket.close()
            return

        # Build remote URL
        final_url = f"wss://{AGENT_URL}/ws/{user_id}?is_audio={is_audio}"
        logger.debug(f"Connecting to agent URL: {final_url}")

        # Create and start WebSocket handler
        websocket_handler = WebsocketHandler(user_id, is_audio, final_url, websocket)
        await websocket_handler.connect()

    except Exception as e:
        logger.error(f"WebSocket proxy error for user {user_id}: {e}")
        try:
            if not websocket.client_state.CONNECTED:
                await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": f"Internal server error: {str(e)}"
            }))
            await websocket.close()
        except Exception:
            pass  # Connection might already be closed

# Here will be a websocket built for the telnyx phone
