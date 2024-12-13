import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from vosk import Model, KaldiRecognizer
import json
import logging
import shutil
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI()

ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    logger.error("Không tìm thấy ffmpeg trong PATH. Vui lòng cài đặt ffmpeg hoặc thêm ffmpeg vào PATH.")
    sys.exit("ffmpeg not found in PATH. Exiting.")

logger.info(f"ffmpeg path: {ffmpeg_path}")

custom_words = ["xin chào", "việt nam", "công nghệ", "machine learning", "trí tuệ nhân tạo","nguyễn trường giang","Donal Trump","ukraina","tiên nhân phủ đỉnh",'trần lê văn đức','trần','lê']

model = Model(lang="vn", model_name="vosk-model-vn-0.4")

# Tuỳ chọn: Thêm custom words vào grammar, nếu cần
# custom_words = ["xin chào", "việt nam", "công nghệ", "machine learning", "trí tuệ nhân tạo"]
recognizer = KaldiRecognizer(model, 16000, json.dumps(custom_words))

async def read_ffmpeg_stdout(process, recognizer, websocket):
    try:
        while True:
            pcm_data = await process.stdout.read(4096)
            if not pcm_data:
                break
            if recognizer.AcceptWaveform(pcm_data):
                # Chỉ gửi final result khi một câu được hoàn thiện
                result = json.loads(recognizer.Result())
                text = result.get('text', '').strip()
                if text:
                    await websocket.send_text(text + " ")
    except Exception as e:
        logger.error("Error reading ffmpeg stdout:", exc_info=True)

async def log_ffmpeg_stderr(process):
    try:
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            logger.error(f"ffmpeg stderr: {line.decode('utf-8').strip()}")
    except Exception as e:
        logger.error("Error reading ffmpeg stderr:", exc_info=True)

@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    # Khởi tạo recognizer
    # Nếu không dùng custom words:

    # recognizer = KaldiRecognizer(model, 16000, json.dumps(custom_words))
    recognizer.SetWords(True)

    ffmpeg_executable = ffmpeg_path

    # Giả sử frontend gửi audio/webm; codecs=opus
    ffmpeg_command = [
        ffmpeg_executable,
        "-y",
        "-f", "webm",
        "-c:a", "libopus",
        "-i", "pipe:0",
        "-ar", "16000",
        "-ac", "1",
        "-f", "s16le",
        "pipe:1"
    ]
    logger.info(f"Starting ffmpeg subprocess with command: {' '.join(ffmpeg_command)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        logger.error("Error starting ffmpeg subprocess:", exc_info=True)
        await websocket.send_text(f"Server error: {e}")
        await websocket.close(code=1011, reason="FFmpeg initialization error.")
        return

    stderr_task = asyncio.create_task(log_ffmpeg_stderr(process))
    read_task = asyncio.create_task(read_ffmpeg_stdout(process, recognizer, websocket))

    try:
        while True:
            try:
                data = await websocket.receive_bytes()
            except WebSocketDisconnect:
                logger.info("Client disconnected")
                break
            except Exception as e:
                logger.error("Error receiving data:", exc_info=True)
                if websocket.client_state.name != "DISCONNECTED":
                    await websocket.close(code=1011, reason=f"Server error: {e}")
                break

            if not data:
                await websocket.send_text("[Warning] Received empty audio data.")
                continue

            try:
                process.stdin.write(data)
                await process.stdin.drain()
                logger.info(f"Received audio chunk of size: {len(data)} bytes")
            except Exception as e:
                logger.error("Error writing to ffmpeg stdin:", exc_info=True)
                await websocket.send_text(f"STT processing error: {e}")
                if websocket.client_state.name != "DISCONNECTED":
                    await websocket.close(code=1011, reason=f"STT processing error: {e}")
                break

    finally:
        try:
            if process.stdin:
                process.stdin.close()
                await process.stdin.wait_closed()
        except Exception as e:
            logger.warning("Error closing ffmpeg stdin:", exc_info=True)

        await read_task
        await stderr_task
        await process.wait()

        # Lấy kết quả cuối nếu có
        try:
            final_result = json.loads(recognizer.FinalResult())
            final_text = final_result.get('text', '').strip()
            if final_text and websocket.client_state.name == "CONNECTED":
                await websocket.send_text(final_text + " ")
        except Exception as e:
            logger.warning("Error finalizing transcription:", exc_info=True)

        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.warning("Error closing WebSocket:", exc_info=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
