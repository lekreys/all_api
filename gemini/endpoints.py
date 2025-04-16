import asyncio
import json
import os
import base64
from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect , APIRouter , File, UploadFile, Form, HTTPException , Header
from google import genai
from google.genai import types
from fastapi.responses import JSONResponse
import io
from pydantic import BaseModel
from typing import List, Optional

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







@router.post("/generate-image/")
async def generate_image(file: UploadFile = File(...), prompt: str = Form(...) ,  x_api_key: str = Header(...)):

    try:
        client = genai.Client(api_key=x_api_key)

        input_image_bytes = await file.read()
        
        with open("temp_input.jpeg", "wb") as f:
            f.write(input_image_bytes)

        uploaded_file = client.files.upload(file="temp_input.jpeg")

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=uploaded_file.mime_type,
                    ),
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_modalities=["image", "text"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_CIVIC_INTEGRITY",
                    threshold="OFF",
                ),
            ],
            response_mime_type="text/plain",
        )

        generated_image_bytes = None

        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash-exp-image-generation",
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            
            if chunk.candidates[0].content.parts[0].inline_data:
                generated_image_bytes = chunk.candidates[0].content.parts[0].inline_data.data
                break

        os.remove("temp_input.jpeg")

        if not generated_image_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate image")

        image_base64 = base64.b64encode(generated_image_bytes).decode('utf-8')

        return {
            'image_base64': image_base64
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


