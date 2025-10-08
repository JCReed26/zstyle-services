# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import json
import logging
from collections.abc import Callable
from pathlib import Path

import backoff
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequest, LiveRequestQueue
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines import _utils
from websockets.exceptions import ConnectionClosedError

from .agent import root_agent
from .utils.typing import Feedback

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the path to the frontend build directory
current_dir = Path(__file__).parent
frontend_build_dir = current_dir.parent / "frontend" / "build"

# Mount static files if build directory exists
if frontend_build_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(frontend_build_dir / "static")),
        name="static",
    )
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
logging.basicConfig(level=logging.INFO)


# Initialize ADK services
session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()
memory_service = InMemoryMemoryService()

# Initialize ADK runner
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
    app_name="live-app",
)


class AgentSession:
    """Manages bidirectional communication between a client and the agent."""

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize the agent session.

        Args:
            websocket: The client websocket connection
        """
        self.websocket = websocket
        self.input_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.user_id: str | None = None
        self.session_id: str | None = None

    async def receive_from_client(self) -> None:
        """Listen for messages from the client and put them in the queue."""
        while True:
            try:
                message = await self.websocket.receive()

                if "text" in message:
                    data = json.loads(message["text"])

                    if isinstance(data, dict):
                        # Skip setup messages - they're for backend logging only
                        if "setup" in data:
                            logger.log_struct(
                                {**data["setup"], "type": "setup"}, severity="INFO"
                            )
                            logging.info(
                                "Received setup message (not forwarding to agent)"
                            )
                            continue

                        # Forward message to agent engine
                        await self.input_queue.put(data)
                    else:
                        logging.warning(
                            f"Received unexpected JSON structure from client: {data}"
                        )

                elif "bytes" in message:
                    # Handle binary data
                    await self.input_queue.put({"binary_data": message["bytes"]})

                else:
                    logging.warning(
                        f"Received unexpected message type from client: {message}"
                    )

            except ConnectionClosedError as e:
                logging.warning(f"Client closed connection: {e}")
                break
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON from client: {e}")
                break
            except Exception as e:
                logging.error(f"Error receiving from client: {e!s}")
                break

    async def run_agent(self) -> None:
        """Run the agent with the input queue using bidi_stream_query protocol."""
        try:
            # Send setupComplete immediately
            setup_complete_response: dict = {"setupComplete": {}}
            await self.websocket.send_json(setup_complete_response)

            # Wait for first request with user_id
            first_request = await self.input_queue.get()
            self.user_id = first_request.get("user_id")
            if not self.user_id:
                raise ValueError("The first request must have a user_id.")

            self.session_id = first_request.get("session_id")
            first_live_request = first_request.get("live_request")

            # Create session if needed
            if not self.session_id:
                session = await session_service.create_session(
                    app_name="live-app",
                    user_id=self.user_id,
                )
                self.session_id = session.id

            # Create LiveRequestQueue
            live_request_queue = LiveRequestQueue()

            # Add first live request if present
            if first_live_request and isinstance(first_live_request, dict):
                live_request_queue.send(LiveRequest.model_validate(first_live_request))

            # Forward requests from input_queue to live_request_queue
            async def _forward_requests() -> None:
                while True:
                    request = await self.input_queue.get()
                    live_request = LiveRequest.model_validate(request)
                    live_request_queue.send(live_request)

            # Forward events from agent to websocket
            async def _forward_events() -> None:
                events_async = runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=live_request_queue,
                )
                async for event in events_async:
                    event_dict = _utils.dump_event_for_json(event)
                    await self.websocket.send_json(event_dict)

                    # Check for error responses
                    if isinstance(event_dict, dict) and "error" in event_dict:
                        logging.error(f"Agent error: {event_dict['error']}")
                        break

            # Run both tasks
            requests_task = asyncio.create_task(_forward_requests())

            try:
                await _forward_events()
            finally:
                requests_task.cancel()
                try:
                    await requests_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logging.error(f"Error in agent: {e}")
            await self.websocket.send_json({"error": str(e)})


def get_connect_and_run_callable(websocket: WebSocket) -> Callable:
    """Create a callable that handles agent connection with retry logic.

    Args:
        websocket: The client websocket connection

    Returns:
        Callable: An async function that establishes and manages the agent connection
    """

    async def on_backoff(details: backoff._typing.Details) -> None:
        await websocket.send_json(
            {
                "status": f"Model connection error, retrying in {details['wait']} seconds..."
            }
        )

    @backoff.on_exception(
        backoff.expo, ConnectionClosedError, max_tries=10, on_backoff=on_backoff
    )
    async def connect_and_run() -> None:
        logging.info("Starting ADK agent")
        session = AgentSession(websocket)

        logging.info("Starting bidirectional communication with agent")
        await asyncio.gather(
            session.receive_from_client(),
            session.run_agent(),
        )

    return connect_and_run


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle new websocket connections."""
    await websocket.accept()
    connect_and_run = get_connect_and_run_callable(websocket)
    await connect_and_run()


@app.get("/")
async def serve_frontend_root() -> FileResponse:
    """Serve the frontend index.html at the root path."""
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run 'npm run build' in the frontend directory.",
    )


@app.get("/{full_path:path}")
async def serve_frontend_spa(full_path: str) -> FileResponse:
    """Catch-all route to serve the frontend for SPA routing.

    This ensures that client-side routes are handled by the React app.
    Excludes API routes (ws, feedback) and static assets.
    """
    # Don't intercept API routes
    if full_path.startswith(("ws", "feedback", "static", "api")):
        raise HTTPException(status_code=404, detail="Not found")

    # Serve index.html for all other routes (SPA routing)
    index_file = frontend_build_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run 'npm run build' in the frontend directory.",
    )


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
