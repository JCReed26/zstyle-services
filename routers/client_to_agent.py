"""
Simple WebSocket Proxy for Agent Connect Server
"""

from fastapi import WebSocket, WebSocketDisconnect, APIRouter
import websockets
import asyncio
import os
import json
from dotenv import load_dotenv
import logging
import time
from typing import Dict, Set

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

# Connection tracking for deduplication and rate limiting
active_connections: Dict[str, WebSocket] = {}
connection_attempts: Dict[str, list] = {}
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_CONNECTIONS_PER_MINUTE = 10

async def forward_client_to_agent(client_ws: WebSocket, agent_ws):
    """Forward messages from client to agent"""
    try:
        while True:
            message = await client_ws.receive_text()
            await agent_ws.send(message)
            logger.debug("Forwarded message from client to agent")
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error forwarding client to agent: {e}")

async def forward_agent_to_client(agent_ws, client_ws: WebSocket):
    """Forward messages from agent to client"""
    try:
        while True:
            message = await agent_ws.recv()
            if isinstance(message, str):
                await client_ws.send_text(message)
            else:
                await client_ws.send_bytes(message)
            logger.debug("Forwarded message from agent to client")
    except websockets.exceptions.ConnectionClosed:
        logger.info("Agent connection closed")
    except Exception as e:
        logger.error(f"Error forwarding agent to client: {e}")

def check_rate_limit(user_id: str) -> bool:
    """Check if user is within rate limits"""
    current_time = time.time()
    
    # Clean old attempts
    if user_id in connection_attempts:
        connection_attempts[user_id] = [
            attempt_time for attempt_time in connection_attempts[user_id]
            if current_time - attempt_time < RATE_LIMIT_WINDOW
        ]
    else:
        connection_attempts[user_id] = []
    
    # Check rate limit
    if len(connection_attempts[user_id]) >= MAX_CONNECTIONS_PER_MINUTE:
        return False
    
    # Record this attempt
    connection_attempts[user_id].append(current_time)
    return True

@router.websocket("/ws/{user_id}")
async def simple_websocket_proxy(websocket: WebSocket, user_id: str, is_audio: str = "false"):
    """Simple WebSocket proxy - direct connection to agent"""
    agent_ws = None
    try:
        logger.info(f"User {user_id} connecting (audio: {is_audio})")
        
        # Check rate limiting before accepting connection
        if not check_rate_limit(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            await websocket.close(code=1008, reason="Too many connection attempts")
            return
        
        # Check for existing connection
        if user_id in active_connections:
            logger.warning(f"Duplicate connection attempt for user {user_id}, closing existing")
            try:
                existing_ws = active_connections[user_id]
                await existing_ws.close(code=1000, reason="New connection established")
            except:
                pass
            finally:
                del active_connections[user_id]
        
        # Accept client connection
        await websocket.accept()
        logger.info(f"Accepted connection for user {user_id}")
        
        # Track this connection
        active_connections[user_id] = websocket

        # Determine protocol
        if "localhost" in AGENT_URL or "127.0.0.1" in AGENT_URL:
            protocol = "ws"
        else:
            protocol = "wss"

        # Connect to agent with retry logic
        agent_url = f"{protocol}://{AGENT_URL}/ws/{user_id}?is_audio={is_audio}"
        logger.info(f"Connecting to agent: {agent_url}")
        
        try:
            agent_ws = await asyncio.wait_for(
                websockets.connect(agent_url),
                timeout=30
            )
            logger.info(f"Connected to agent for user {user_id}")
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 429:
                logger.error(f"Agent rate limited for user {user_id}")
                await websocket.send_text(json.dumps({
                    "error": "server rejected WebSocket connection: HTTP 429"
                }))
                return
            else:
                raise

        # Start bidirectional forwarding
        await asyncio.gather(
            forward_client_to_agent(websocket, agent_ws),
            forward_agent_to_client(agent_ws, websocket),
            return_exceptions=True
        )

    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to agent for user {user_id}")
        try:
            await websocket.send_text(json.dumps({
                "error": "Agent service temporarily unavailable"
            }))
        except:
            pass
    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 429:
            logger.error(f"WebSocket proxy error for user {user_id}: server rejected WebSocket connection: HTTP 429")
            try:
                await websocket.send_text(json.dumps({
                    "error": "server rejected WebSocket connection: HTTP 429"
                }))
            except:
                pass
        else:
            logger.error(f"WebSocket proxy error for user {user_id}: {e}")
            try:
                await websocket.send_text(json.dumps({
                    "error": f"server rejected WebSocket connection: HTTP {e.status_code}"
                }))
            except:
                pass
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
        if user_id in active_connections:
            del active_connections[user_id]
        
        if agent_ws:
            try:
                await agent_ws.close()
            except:
                pass
        try:
            await websocket.close()
        except:
            pass
        logger.info(f"Cleaned up connection for user {user_id}")

@router.get("/health")
async def health_check():
    """Simple health check"""
    return {
        "status": "healthy",
        "service": "simple-websocket-proxy",
        "agent_url": AGENT_URL
    }
