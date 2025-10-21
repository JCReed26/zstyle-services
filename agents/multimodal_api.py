import asyncio
import base64
import json

from app.agent import root_agent
from google.adk.agents import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

from utils.common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
    SYSTEM_INSTRUCTION
)

class MultimodalAdkServer(BaseWebSocketServer):
    """Websocket server implementation for multimodal input (audio + video)"""
    def __init__(self, host="0.0.0.0", port=4312):
        super().__init__(host, port)
        self.session_service = InMemorySessionService()
        self.agent = root_agent

    async def process_audio(self, websocket, client_id):
        self.active_clients[client_id] = websocket

        # create session for the client
        session = await self.session_service.create_session(
            app_name="zstyle",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )

        # create runner
        runner = Runner(
            app_name="zstyle",
            agent=self.agent,
            session_service=self.session_service
        )

        # live request queue
        live_request_queue = LiveRequestQueue()

        # create run config with audio settings 
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
            response_modalities=["Audio", "Text"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig()
        )

        audio_queue = asyncio.Queue()
        text_queue = asyncio.Queue()
        video_queue = asyncio.Queue() # video might not be implemented till later 

        async with asyncio.TaskGroup() as tg:
            async def handle_websocket_messages():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        # decode base64 bytes
                        if data.get("type") == "audio":
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            await audio_queue.put(audio_bytes)

                        elif data.get("type") == "video":
                            video_bytes = base64.b64decode(data.get("data", ""))
                            video_mode = data.get(
                                "mode", "webcam"
                            )
                            await video_queue.put(
                                {"data": video_bytes, "mode": video_mode}
                            )

                        elif data.get("type") == "text":
                            user_text = data.get("data", "").strip()
                            await text_queue.put(user_text)

                        elif data.get("type") == "end":
                            logger.info("Received end signal from client")

                    except json.JSONDecodeError:
                        logger.error("Invalid JSON message received")

                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
            
            async def process_and_send_audio():
                while True:
                    data = await audio_queue.get()

                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data,
                            mime_type=f"audio.pcm;rate={SEND_SAMPLE_RATE}",
                        )
                    )

                    audio_queue.task_done()

            async def process_and_send_text():
                while True:
                    data = await text_queue.get()
                    
                    live_request_queue.send_realtime(
                        types.Content(
                            parts=[types.Part(text=data)],
                            role="user"
                        )
                    )

                    text_queue.task_done()

            async def process_and_send_video():
                while True:
                    video_data = await video_queue.get()

                    video_bytes = video_data.get("data")
                    video_mode = video_data.get("mode", "webcam")

                    logger.info(f"Processing video frame from {video_mode}")

                    live_request_queue.send_realtime(
                        types.Blob(
                            data=video_bytes,
                            mime_type="image/jpeg"
                        )
                    )

                    video_queue.task_done()

            async def receive_and_process_responses():
                input_texts = []
                output_texts = []
                current_session_id = None

                interrupted = False

                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    event_str = str(event)

                    # if session resuption update, store the sessionID
                    if hasattr(event, "session_resumption_update") and event.live_session_resumption_update:
                        update = event.live_session_resumption_update
                        if update.resumable and update.new_handle:
                            current_session_id = update.new_handle
                            logger.info(f"New Session: {current_session_id}")
                            # send id to client TODO database too
                            session_id_msg = json.dumps(
                                {"type": "session_id", "data": current_session_id}
                            )
                            await websocket.send(session_id_msg)

                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # process audio content
                            if hasattr(part, "inline_data") and part.inline_data:
                                b64_audio = base64.b64encode(
                                    part.inline_data.data
                                ).decode("utf-8")
                                await websocket.send(
                                    json.dumps({"type": "audio", "data": b64_audio})
                                )
                            
                            # process text 
                            if hasattr(part, "text") and part.text:
                                if hasattr(event.content, "role") and event.content.role == "user":
                                    input_texts.append(part.text)
                                else:
                                    # process partial messages drop empty ones
                                    if "partial=True" in event_str:
                                        await websocket.send(
                                            json.dumps(
                                                {"type": "text", "data": part.text}
                                            )
                                        )
                                        output_texts.append(part.text)
                            
                    if event.interrupted and not interrupted:
                        logger.info("INTERUPTION DETECTED")
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "interrupted",
                                    "data": "Response interrupted by user input"
                                }
                            )
                        )

                    if event.turn_complete:
                        if not interrupted:
                            logger.info("yapping complete")
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "turn_complete",
                                        "session_id": current_session_id, 
                                    }
                                )
                            )
                        
                        if input_texts:
                            unique_texts = list(dict.fromkeys(input_texts))
                            # WARNING: potentially costly log
                            logger.info(
                                f"Output transaction: {' '.join(unique_texts)}"
                            )

                        if output_texts:
                            unique_texts = list(dict.fromkeys(output_texts))
                            # WARNING: potentially costly log
                            logger.info(
                                f"Output transaction: {' '.join(unique_texts)}"
                            )

                        input_texts = []
                        output_texts = []
                        interrupted = False
            
            tg.create_task(handle_websocket_messages(), name="MessageHandler")
            tg.create_task(process_and_send_audio(), name="AudioProcessor")
            tg.create_task(process_and_send_text(), name="TextProcessor")
            tg.create_task(process_and_send_video(), name="VideoProcessor")
            tg.create_task(receive_and_process_responses(), name="ResponseHandler")

async def main():
    server = MultimodalAdkServer()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting application via keyboard input")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        import traceback

        traceback.print_exc()