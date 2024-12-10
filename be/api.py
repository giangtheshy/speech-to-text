from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from RealtimeSTT import AudioToTextRecorder  # Ensure RealtimeSTT is installed correctly
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI()

@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    try:
        # Initialize the AudioToTextRecorder
        try:
            recorder = AudioToTextRecorder(use_microphone=False)
            logger.info("RealtimeSTT recorder initialized successfully.")
        except FileNotFoundError as fnf_error:
            logger.error(f"FFmpeg extension not found: {fnf_error}")
            await websocket.send_text("Server error: FFmpeg extensions are missing. Please install FFmpeg and ensure it's in your PATH.")
            await websocket.close(code=1011, reason="FFmpeg extensions missing.")
            return
        except Exception as e:
            logger.error(f"Error initializing RealtimeSTT: {e}")
            await websocket.send_text(f"Server error: {e}")
            await websocket.close(code=1011, reason=f"Initialization error: {e}")
            return

        while True:
            try:
                # Receive audio chunk from client
                data = await websocket.receive_bytes()
                if not data:
                    await websocket.send_text("[Warning] Received empty audio data.")
                    continue

                # Feed audio data into the recorder
                try:
                    # recorder.feed_audio(data)
                    # transcription = recorder.text()
                    transcription = "okie nhe "
                    
                    if transcription:
                        await websocket.send_text(transcription + " ")
                except Exception as processing_error:
                    logger.error(f"Error processing audio: {processing_error}")
                    await websocket.send_text(f"STT processing error: {processing_error}")
                    await websocket.close(code=1011, reason=f"STT processing error: {processing_error}")
                    break

            except WebSocketDisconnect:
                logger.info("Client disconnected")
                break
            except Exception as receive_error:
                logger.error(f"Error receiving data: {receive_error}")
                await websocket.send_text(f"Server error: {receive_error}")
                await websocket.close(code=1011, reason=f"Server error: {receive_error}")
                break

    finally:
        # Attempt to end the STT session gracefully
        try:
            if 'recorder' in locals() and hasattr(recorder, 'end_session'):
                recorder.end_session()
                logger.info("RealtimeSTT session ended.")
        except Exception as end_error:
            logger.warning(f"Error ending STT session: {end_error}")

        # Ensure the WebSocket connection is closed
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close()
            logger.info("WebSocket connection closed")


