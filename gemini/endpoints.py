import asyncio
import json
import os
import base64
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect , APIRouter
from google import genai


load_dotenv() 

router = APIRouter()

MODEL = "gemini-2.0-flash-exp"

client = genai.Client(
    api_key=  os.getenv('GEMINI_API_KEY'),
    http_options={
        'api_version': 'v1alpha',

    }
)

@router.websocket("/ws")
async def gemini_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        config_message = await websocket.receive_text()
        config_data = json.loads(config_message)
        config = config_data.get("setup", {})

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API")
            
            async def send_to_gemini():
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        if "realtime_input" in data:
                            for chunk in data["realtime_input"]["media_chunks"]:
                                if chunk["mime_type"] == "audio/pcm":
                                    await session.send({"mime_type": "audio/pcm", "data": chunk["data"]})
                                elif chunk["mime_type"] == "image/jpeg":
                                    await session.send({"mime_type": "image/jpeg", "data": chunk["data"]})
                except WebSocketDisconnect:
                    print("Client disconnected during send")
                except Exception as e:
                    print(f"Error sending to Gemini: {e}")
                finally:
                    print("send_to_gemini closed")

            async def receive_from_gemini():
                try:
                    while True:
                        async for response in session.receive():
                            print(f"response: {response}")
                            if response.server_content is None:
                                print(f"Unhandled server message! - {response}")
                                continue

                            model_turn = response.server_content.model_turn
                            if model_turn:
                                for part in model_turn.parts:
                                    if hasattr(part, 'text') and part.text is not None:
                                        await websocket.send_text(json.dumps({"text": part.text}))
                                    elif hasattr(part, 'inline_data') and part.inline_data is not None:
                                        print("audio mime_type:", part.inline_data.mime_type)
                                        base64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                        await websocket.send_text(json.dumps({"audio": base64_audio}))
                                        print("audio received")

                            if response.server_content.turn_complete:
                                print("<Turn complete>")
                except WebSocketDisconnect:
                    print("Client disconnected during receive")
                except Exception as e:
                    print(f"Error receiving from Gemini: {e}")
                finally:
                    print("receive_from_gemini closed")
            send_task = asyncio.create_task(send_to_gemini())
            receive_task = asyncio.create_task(receive_from_gemini())
            await asyncio.gather(send_task, receive_task)

    except Exception as e:
        print(f"Error in Gemini session: {e}")
    finally:
        await websocket.close()
        print("Gemini session closed.")
