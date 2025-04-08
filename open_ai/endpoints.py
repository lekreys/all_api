from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
import json
import logging
import ssl
import websockets
from typing import Dict, Optional
from dotenv import load_dotenv
from open_ai import models
from open_ai.database import Base, declarative_base, Sensionalocal, Engine, Client
from sqlalchemy.orm import Session
from datetime import datetime
from open_ai.schemas import Conversation
import uuid
import os

router = APIRouter()

Base.metadata.create_all(Engine)

def get_db():
    db = Sensionalocal()
    try:
        yield db
    finally:
        db.close()

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
 
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_json_response(self, data: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)

manager = ConnectionManager()

class OpenAIRealtimeClient:

    def __init__(self, instructions: str, client_id: str, voice: str = "alloy"):
        
        self.url = 'wss://gpt4o-realtime.openai.azure.com/openai/realtime?api-version=2024-10-01-preview&deployment=gpt-4o-realtime-preview'  #"wss://api.openai.com/v1/realtime"
        self.model = "gpt-4o-realtime-preview-2024-10-01"
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.instructions = instructions
        self.voice = voice
        self.client_id = client_id
        self.audio_buffer = b''
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        self.session_config = {
            "modalities": ["audio", "text"],
            "instructions": self.instructions,
            "voice": self.voice,
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": None,
            "input_audio_transcription": {
                "model": "whisper-1"
            },
            "temperature": 0.6
        }

    async def connect(self):
        logger.info(f"Connecting to OpenAI WebSocket: {self.url}")
        headers = {
            "api-key": self.api_key,       # f"Bearer {self.api_key}",
        }
        
        self.ws = await websockets.connect(
            self.url,
            extra_headers=headers,
            ssl=self.ssl_context
        )
        logger.info("Connected to OpenAI Realtime API")

        await self.send_event({
            "type": "session.update",
            "session": self.session_config
        })
        await self.send_event({"type": "response.create"})

    async def send_event(self, event):
        if self.ws:
            await self.ws.send(json.dumps(event))
            logger.debug(f"Event sent - type: {event['type']}")

    async def handle_openai_messages(self):
        try:
            async for message in self.ws:
                event = json.loads(message)
                await self.handle_event(event)
        except websockets.ConnectionClosed as e:
            logger.error(f"OpenAI WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error handling OpenAI messages: {e}")

    async def handle_event(self, event):
        event_type = event.get("type")
        
        if event_type == "error":
            await manager.send_json_response({
                "type": "error",
                "message": event['error']['message']
            }, self.client_id)
        
        elif event_type == "response.audio.delta":
            await manager.send_json_response({
                "type": "audio",
                "data": event["delta"]
            }, self.client_id)
        
        elif event_type == "response.text.delta":
            await manager.send_json_response({
                "type": "text",
                "data": event["delta"]
            }, self.client_id)
        
        elif event_type == "response.done":
            response = event.get("response", {})
            usage = response.get("usage", {})
            output = response.get("output", [])
            
            transcript = ""
            if output and len(output) > 0:
                content = output[0].get("content", [])
                if content and len(content) > 0:
                    transcript = content[0].get("transcript", "")

            await manager.send_json_response({
                "type": "completion",
                "total_tokens": usage.get("total_tokens", 0),
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "transcript": transcript
            }, self.client_id)

    async def process_audio(self, base64_audio: str):
        try:
            await self.send_event({
                "type": "input_audio_buffer.append",
                "audio": base64_audio
            })
            await self.send_event({"type": "input_audio_buffer.commit"})
            await self.send_event({"type": "response.create"})
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await manager.send_json_response({
                "type": "error",
                "message": f"Error processing audio: {str(e)}"
            }, self.client_id)

    async def cleanup(self):
        if self.ws:
            await self.ws.close()

@router.websocket("/ws/{client_id}/{voice}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, voice: str):
    openai_client = OpenAIRealtimeClient(
        instructions="kamu adalah planner perjalanan yang akan membantu user  , jawab dalam 2 kalimat",
        client_id=client_id,
        voice=voice
    )
    
    try:
        await manager.connect(websocket, client_id)
        await openai_client.connect()
        
        openai_handler = asyncio.create_task(openai_client.handle_openai_messages())
        
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio":
                await openai_client.process_audio(data["data"])
            elif data["type"] == "close":
                break
            
                
    

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}")
    finally:
        manager.disconnect(client_id)
        await openai_client.cleanup()
        if 'openai_handler' in locals():
            openai_handler.cancel()

@router.post("/conversation")
def post_feature_request(request: Conversation, db: Session = Depends(get_db)):
    conversation = models.Conversation(

        id_conversation=request.id_conversation,
        user_message=request.user_message,
        agent_message=request.agent_message,
        timestamp=datetime.now(),
        input_token = request.input_token,
        output_token = request.output_token,
        total_token  = request.total_token,
        transcript = request.transcript
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.post("/create-conversation-id")
def create_id():
    new_id = uuid.uuid4()
    return {"conversation_id": new_id}
