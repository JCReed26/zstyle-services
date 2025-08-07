from fastapi import WebSocket, WebSocketDisconnect, APIRouter, status
import asyncio
from .agent_handlers.main_agent import start_agent_session, agent_to_client_messaging, client_to_agent_messaging
from vertexai import agent_engines
from google.adk.agents.run_config import RunConfig
import json

import os
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
AGENT_RESOURCE_NAME = os.getenv("AGENT_RESOURCE_NAME")


router = APIRouter(prefix="/conn")

response_counter = 0 # TESTING ONLY 

class Websockethandler:
    # establishes list of active websockets on server - using a dictionary to track each user's connection
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    # accept the websocket connection and add to open sockets, indexed by user_id
    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_voice_message(self, message: str, websocket: WebSocket):
        await websocket.send_bytes(message)

socket = Websockethandler()

# Start Text Related Endpoints

@router.websocket("/ws/{user_id}")
async def websocket_endpt(websocket: WebSocket, user_id: str, is_audio: str):
    """ADK GIVEN Client websocket endpoint"""
    # Wait for client connection
    await socket.connect(user_id, websocket)
    print(f"Client #{user_id} connected, audio mode; {is_audio}")

    # Start agent session
    user_id_str = str(user_id)
    live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == 'true')

    # Start tasks
    agent_to_client_task = asyncio.create_task(agent_to_client_messaging(websocket, live_events))
    client_to_agent_task = asyncio.create_task(client_to_agent_messaging(websocket, live_request_queue))

    try:
        # Wait until the websocket is disconnected or an error occurs 
        tasks = [agent_to_client_task, client_to_agent_task]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    finally:
        # Cancel the tasks to ensure they are stopped
        agent_to_client_task.cancel()
        client_to_agent_task.cancel()

    # Close LiveRequestQueue
    live_request_queue.close()

    socket.disconnect(user_id)
    print(f"Client #{user_id} disconnected")


# AI GENERATED
async def async_generator_wrapper(sync_gen):
    """Wraps a synchronous generator to be used in an async for loop."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            # Run the next() call in a separate thread
            item = await loop.run_in_executor(None, next, sync_gen)
            yield item
        except StopIteration:
            # The generator is exhausted
            break

# MOSTLY AI GENERATED
@router.websocket("/test/ws/{user_id}")
async def websocket_test_endpt(websocket: WebSocket, user_id: str, is_audio: str):
    """
    WebSocket endpoint for client-agent communication.
    Receives messages from the client, forwards them to Agent Engine,
    and streams back Agent Engine's responses.
    """
    await websocket.accept()
    print(f"WebSocket connected for user_id: {user_id}")

    remote_agent = None
    try:
        # Attempt to get the remote agent instance
        print(f"Attempting to load agent: {AGENT_RESOURCE_NAME}")
        remote_agent = agent_engines.get(AGENT_RESOURCE_NAME)
        print(f"Successfully loaded agent: {AGENT_RESOURCE_NAME}")

    except Exception as e:
        error_message = f"Failed to load Agent Engine agent: {e}. Please check AGENT_RESOURCE_NAME and permissions."
        print(error_message)
        await websocket.send_json({"type": "error", "content": error_message})
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    try:
        # Define the run configuration for the agent (e.g., response modality)
        # ADK's RunConfig can be passed to the Agent Engine's query methods
        run_config = RunConfig(response_modalities=["TEXT"]) # You can add "AUDIO" if your agent supports it

        while True:
            # 1. Receive message from client
            try:
                data = await websocket.receive_json()
                client_message = data.get("message")
                request_type = data.get("type", "text_input") # e.g., "text_input", "audio_input"

                if not client_message:
                    await websocket.send_json({"type": "error", "content": "No 'message' field in client input."})
                    continue

                print(f"Received from client ({user_id}): {client_message}")

                # 2. Send message to Agent Engine and stream responses
                # Use stream_query for real-time, token-by-token streaming
                agent_stream = remote_agent.stream_query(
                    user_id=user_id,
                    message=client_message,
                    run_config=run_config
                )

                # Send a "start" event to the client if desired, before streaming actual content
                await websocket.send_json({"type": "agent_response_start", "session_id": user_id})

                async for event in async_generator_wrapper(agent_stream):
                    # Agent Engine's stream_query yields objects (e.g., AgentEngineResponse)
                    # You'll need to inspect the 'event' object to extract the relevant content.
                    # This often contains 'text' or 'tool_code' depending on the agent's actions.
                    # The exact structure can vary based on your agent's ADK definition.

                    # For simplicity, let's assume the event object has a 'text' attribute
                    # or can be serialized directly. You might need to adjust this
                    # based on the actual output of your ADK agent when deployed.

                    # Example: Assuming event object can be converted to a dictionary or has a 'text' field
                    if hasattr(event, 'text') and event.text:
                        response_content = event.text
                        await websocket.send_json({"type": "agent_text_chunk", "content": response_content})
                        # print(f"Sent chunk to client: {response_content[:50]}...")
                    elif isinstance(event, dict):
                        # If the event is already a dictionary, send it directly
                        await websocket.send_json({"type": "agent_event", "content": event})
                    else:
                        # Fallback for other types of events, convert to string
                        await websocket.send_json({"type": "agent_event_raw", "content": str(event)})
                
                # Send a "completion" event when the agent's turn is done
                await websocket.send_json({"type": "agent_response_end", "session_id": user_id})
                print(f"Agent response complete for user_id: {user_id}")

            except json.JSONDecodeError:
                print(f"Invalid JSON received from client ({user_id}).")
                await websocket.send_json({"type": "error", "content": "Invalid JSON format."})
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for user_id: {user_id}")
                break # Exit the loop if client disconnects
            except Exception as e:
                print(f"An error occurred during communication for user_id {user_id}: {e}")
                await websocket.send_json({"type": "error", "content": f"Server error: {str(e)}"})
                # Consider closing the WebSocket on critical errors:
                # await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                # break

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user_id: {user_id} during initial connection.")
    except Exception as e:
        print(f"Unhandled error before main loop for user_id {user_id}: {e}")