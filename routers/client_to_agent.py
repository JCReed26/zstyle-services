"""
Simple WebSocket Proxy for Agent Connect Server
Redesigned for stability - acts as a simple bidirectional message forwarder
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio
import os
import json
from dotenv import load_dotenv
import logging
from typing import Dict

# Initialize logging
logger = logging.getLogger("agent-connect-server.client_to_agent")
logger.setLevel(logging.INFO)

# Try to initialize Google Cloud Logging, fall back to standard logging
try:
    from google.cloud.logging import Client
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    logging_client = Client()
    handler = CloudLoggingHandler(logging_client)
    logger.addHandler(handler)
    logger.info("Google Cloud Logging initialized successfully")
except Exception as e:
    # Fallback to standard logging for local development
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.warning(f"Using standard logging (Google Cloud Logging unavailable): {e}")

load_dotenv()

# Get AGENT_URL from environment
AGENT_URL = os.getenv("AGENT_URL", "localhost:5000")

# Clean the URL
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

# Simple connection tracking for cleanup
active_connections: Dict[str, WebSocket] = {}

async def forward_messages(client_ws: WebSocket, agent_ws, user_id: str):
    """
    Simple bidirectional message forwarding between client and agent
    """
    async def client_to_agent():
        """Forward messages from client to agent"""
        try:
            while True:
                message = await client_ws.receive_text()
                await agent_ws.send(message)
                logger.debug(f"Forwarded message from client {user_id} to agent")
        except WebSocketDisconnect:
            logger.info(f"Client {user_id} disconnected")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Agent connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"Error in client_to_agent forwarding for {user_id}: {e}")

    async def agent_to_client():
        """Forward messages from agent to client"""
        try:
            while True:
                message = await agent_ws.recv()
                if isinstance(message, str):
                    await client_ws.send_text(message)
                else:
                    await client_ws.send_bytes(message)
                logger.debug(f"Forwarded message from agent to client {user_id}")
        except WebSocketDisconnect:
            logger.info(f"Client {user_id} disconnected")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Agent connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"Error in agent_to_client forwarding for {user_id}: {e}")

    # Run both forwarding tasks concurrently
    try:
        await asyncio.gather(
            client_to_agent(),
            agent_to_client(),
            return_exceptions=True
        )
    except Exception as e:
        logger.error(f"Error in message forwarding for {user_id}: {e}")

@router.websocket("/ws/{user_id}")
async def websocket_proxy(websocket: WebSocket, user_id: str, is_audio: str = "false"):
    """
    Simple WebSocket proxy - direct bidirectional forwarding
    """
    agent_ws = None
    
    try:
        logger.info(f"User {user_id} connecting (audio: {is_audio})")
        
        # Clean up any existing connection for this user
        if user_id in active_connections:
            logger.info(f"Cleaning up existing connection for user {user_id}")
            try:
                old_ws = active_connections[user_id]
                await old_ws.close(code=1000, reason="New connection established")
            except Exception as e:
                logger.debug(f"Error closing old connection for {user_id}: {e}")
            finally:
                del active_connections[user_id]
        
        # Accept the client connection
        await websocket.accept()
        logger.info(f"Accepted connection for user {user_id}")
        
        # Track this connection
        active_connections[user_id] = websocket
        
        # Determine protocol for agent connection
        if "localhost" in AGENT_URL or "127.0.0.1" in AGENT_URL:
            protocol = "ws"
        else:
            protocol = "wss"
        
        # Connect to agent
        agent_url = f"{protocol}://{AGENT_URL}/ws/{user_id}?is_audio={is_audio}"
        logger.info(f"Connecting to agent: {agent_url}")
        
        try:
            agent_ws = await asyncio.wait_for(
                websockets.connect(agent_url),
                timeout=60  # Increased timeout for Cloud Run cold starts
            )
            logger.info(f"Connected to agent for user {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to agent for user {user_id} after 60 seconds")
            await websocket.send_text(json.dumps({
                "error": "Agent service is taking longer than expected to respond. Please try again in a moment."
            }))
            return
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"Agent rejected connection for user {user_id}: HTTP {e.status_code}")
            await websocket.send_text(json.dumps({
                "error": f"Agent service rejected connection: HTTP {e.status_code}"
            }))
            return
        except Exception as e:
            logger.error(f"Failed to connect to agent for user {user_id}: {e}")
            await websocket.send_text(json.dumps({
                "error": "Failed to connect to agent service"
            }))
            return
        
        # Start bidirectional message forwarding
        await forward_messages(websocket, agent_ws, user_id)
        
    except Exception as e:
        logger.error(f"WebSocket proxy error for user {user_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "error": "Connection error"
            }))
        except:
            pass
    finally:
        # Cleanup
        logger.info(f"Cleaning up connection for user {user_id}")
        
        # Remove from active connections
        if user_id in active_connections:
            del active_connections[user_id]
        
        # Close agent connection
        if agent_ws:
            try:
                await agent_ws.close()
            except Exception as e:
                logger.debug(f"Error closing agent connection for {user_id}: {e}")
        
        # Close client connection
        try:
            await websocket.close()
        except Exception as e:
            logger.debug(f"Error closing client connection for {user_id}: {e}")

@router.get("/health")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "service": "simple-websocket-proxy",
        "agent_url": AGENT_URL,
        "active_connections": len(active_connections)
    }
