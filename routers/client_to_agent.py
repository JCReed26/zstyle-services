"""
Enhanced WebSocket Proxy for Agent Connect Server
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio
import os
import json
import time
from typing import Optional
from collections import defaultdict
from dotenv import load_dotenv

import logging

# Initialize logging with Google Cloud fallback
logger = logging.getLogger("agent-connect-server.client_to_agent")
logger.setLevel(logging.INFO)

# Try to initialize Google Cloud Logging, fall back to standard logging
try:
    from google.cloud.logging import Client
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    logging_client = Client()
    handler = CloudLoggingHandler(logging_client)
    logger.addHandler(handler)
    logger.info("Google Cloud Logging initialized successfully for client_to_agent router")
except Exception as e:
    # Fallback to standard logging for local development
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.warning(f"Using standard logging for client_to_agent router (Google Cloud Logging unavailable): {e}")

load_dotenv()

# Get AGENT_URL from environment or use localhost default for development
AGENT_URL = os.getenv("AGENT_URL", "localhost:5000")

# Remove any protocol prefix if present and clean the URL
if AGENT_URL.startswith("http://"):
    AGENT_URL = AGENT_URL[7:]
elif AGENT_URL.startswith("https://"):
    AGENT_URL = AGENT_URL[8:]
elif AGENT_URL.startswith("ws://"):
    AGENT_URL = AGENT_URL[5:]
elif AGENT_URL.startswith("wss://"):
    AGENT_URL = AGENT_URL[6:]

logger.info(f"Agent URL configured as: {AGENT_URL}")

router = APIRouter(prefix="/agent")

# Connection timeouts and limits
CONNECTION_TIMEOUT = 30  # seconds
MAX_CONNECTIONS_PER_USER = 3

class RateLimiter:
    """Rate limiter to prevent connection storms per user"""
    def __init__(self, max_attempts: int = 3, window_seconds: int = 60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: dict[str, list] = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        # Clean old attempts
        self.attempts[user_id] = [
            attempt_time for attempt_time in self.attempts[user_id]
            if now - attempt_time < self.window_seconds
        ]
        
        if len(self.attempts[user_id]) >= self.max_attempts:
            return False
        
        self.attempts[user_id].append(now)
        return True

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

# Global connection manager and rate limiter
connection_manager = ConnectionManager()
rate_limiter = RateLimiter(max_attempts=3, window_seconds=60)

class WebsocketHandler:
    def __init__(self, user_id: str, is_audio: str, remote_url: str, client_ws: WebSocket):
        self.user_id = user_id
        self.is_audio = is_audio
        self.remote_url = remote_url
        self.client_ws = client_ws
        self.remote_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = True

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
            logger.info(f"Attempting to connect to remote: {self.remote_url}")

            # Connect to remote with timeout
            try:
                self.remote_ws = await asyncio.wait_for(
                    websockets.connect(
                        self.remote_url,
                    ),
                    timeout=CONNECTION_TIMEOUT
                )
                logger.info(f"Successfully connected to remote agent for user {self.user_id}")
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout to remote for user {self.user_id}")
                await self.client_ws.send_text(json.dumps({
                    "error": "Agent service temporarily unavailable. Please try again in a few minutes."
                }))
                return
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    logger.error(f"Rate limited by agent service for user {self.user_id}")
                    await self.client_ws.send_text(json.dumps({
                        "error": "Service is busy. Please wait a few minutes before trying again."
                    }))
                else:
                    logger.error(f"Failed to connect to remote for user {self.user_id}: {e}")
                    await self.client_ws.send_text(json.dumps({
                        "error": "Unable to connect to agent service. Please try again later."
                    }))
                return

            # Start bidirectional streaming
            tasks = [
                asyncio.create_task(self._client_to_remote()),
                asyncio.create_task(self._remote_to_client())
            ]
            
            try:
                # Wait for either task to complete (indicating connection closed)
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                # Check for exceptions in completed tasks
                for task in done:
                    try:
                        await task
                    except Exception as e:
                        logger.error(f"Task error for user {self.user_id}: {e}")
                        
            except Exception as e:
                logger.error(f"Error in bidirectional streaming for user {self.user_id}: {e}")

        except Exception as e:
            logger.error(f"Connection error for user {self.user_id}: {e}")
        finally:
            await self._cleanup()

    async def _client_to_remote(self):
        """Handle messages from client to remote agent"""
        try:
            while self._running and self.remote_ws:
                try:
                    # Receive message from client
                    message = await self.client_ws.receive_text()
                    
                    # Forward to remote agent
                    await self.remote_ws.send(message)
                    logger.debug(f"Forwarded message from client {self.user_id} to agent")

                except WebSocketDisconnect:
                    logger.info(f"Client {self.user_id} disconnected")
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
                    # Receive message from remote agent
                    message = await self.remote_ws.recv()
                    
                    # Forward to client
                    if isinstance(message, str):
                        await self.client_ws.send_text(message)
                    else:
                        await self.client_ws.send_bytes(message)
                    
                    logger.debug(f"Forwarded message from agent to client {self.user_id}")

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

        # Close connections
        try:
            if self.remote_ws:
                await self.remote_ws.close()
        except Exception as e:
            logger.debug(f"Error closing remote websocket: {e}")

        try:
            # Check if client websocket is still connected before closing
            if hasattr(self.client_ws, 'client_state') and self.client_ws.client_state.name not in ["DISCONNECTED", "CONNECTING"]:
                await self.client_ws.close()
        except Exception as e:
            logger.debug(f"Error closing client websocket: {e}")

        logger.info(f"Cleaned up connection for user {self.user_id}")

# Health check endpoint for monitoring
@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring WebSocket proxy status"""
    return {
        "status": "healthy",
        "service": "websocket-proxy",
        "agent_url": AGENT_URL,
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
async def websocket_proxy(websocket: WebSocket, user_id: str, is_audio: str = "false"):
    """Main WebSocket proxy endpoint with enhanced error handling"""
    try:
        logger.info(f"User {user_id} is connecting (audio: {is_audio})...")

        # Check rate limiting first
        if not rate_limiter.is_allowed(user_id):
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": "Too many connection attempts. Please wait before retrying."
            }))
            await websocket.close()
            logger.warning(f"Rate limited user {user_id}")
            return

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

        if not AGENT_URL:
            await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": "AGENT_URL environment variable is not set"
            }))
            await websocket.close()
            return

        # Determine protocol based on environment
        # Use ws:// for localhost, wss:// for remote
        if "localhost" in AGENT_URL or "127.0.0.1" in AGENT_URL:
            protocol = "ws"
        else:
            protocol = "wss"

        # Build remote URL
        final_url = f"{protocol}://{AGENT_URL}/ws/{user_id}?is_audio={is_audio}"
        logger.info(f"Connecting to agent URL: {final_url}")

        # Create and start WebSocket handler
        websocket_handler = WebsocketHandler(user_id, is_audio, final_url, websocket)
        await websocket_handler.connect()

    except Exception as e:
        logger.error(f"WebSocket proxy error for user {user_id}: {e}")
        try:
            # Fix the connection state checking bug
            if websocket.client_state.name not in ["CONNECTED", "DISCONNECTED"]:
                await websocket.accept()
            await websocket.send_text(json.dumps({
                "error": f"Internal server error: {str(e)}"
            }))
            await websocket.close()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
