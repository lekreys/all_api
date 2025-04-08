from fastapi import APIRouter, WebSocket, WebSocketDisconnect , HTTPException , Query
import asyncio
import websockets
from elevenlab.schema import CreateAgentRequest
import requests
import os


apikey = os.getenv("ELEVEN_LABS_API_KEY")

router = APIRouter()

@router.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):

    TARGET_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=CCd3IDviRNuN5Hss9s3G"

    await websocket.accept()
    try:
        async with websockets.connect(TARGET_WS_URL) as target_ws:
            async def forward_client_to_target():
                while True:
                    data = await websocket.receive_text()
                    await target_ws.send(data)

            async def forward_target_to_client():
                while True:
                    data = await target_ws.recv()
                    await websocket.send_text(data)

            await asyncio.gather(
                forward_client_to_target(),
                forward_target_to_client()
            )
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.close()
        print("Proxy error:", e)



@router.post("/create_agent")
def create_agent(request: CreateAgentRequest):

    TARGET_URL = "https://api.elevenlabs.io/v1/convai/agents/create"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key' : apikey
    }
    
    response = requests.post(TARGET_URL, json=request.dict() , headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()


@router.get("/agents-list")
def get_agents():

    TARGET_URL = "https://api.elevenlabs.io/v1/convai/agents"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()

@router.get("/detail-agent")
def get_detail_agent(agent_id: str = Query()):

    TARGET_URL = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()





@router.get("/conversation-list")
def get_conversation():

    TARGET_URL = "https://api.elevenlabs.io/v1/convai/conversations"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()




@router.get("/detail-conversation")
def get_detail_conversation(conversation_id: str = Query()):

    TARGET_URL = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()