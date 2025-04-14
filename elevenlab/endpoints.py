from fastapi import FastAPI, WebSocket, WebSocketDisconnect , HTTPException , Header
import asyncio
import websockets
from schema import CreateAgentRequest
import requests


app = FastAPI()


@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket ):

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



@app.post("/create_agent")
def create_agent(request: CreateAgentRequest , apikey: str = Header(...)):

    TARGET_URL = "https://api.elevenlabs.io/v1/convai/agents/create"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key' : apikey
    }
    
    response = requests.post(TARGET_URL, json=request.dict() , headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()



@app.get("/agents-list")
def get_agents(apikey: str = Header(...)):
    TARGET_URL = "https://api.elevenlabs.io/v1/convai/agents"
    
    # Gunakan nilai apikey dari header
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()




@app.get("/detail-agent/{agent_id}")
def get_detail_agent(agent_id : str , apikey: str = Header(...)):

    TARGET_URL = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()





@app.get("/conversation-list")
def get_conversation(apikey: str = Header(...)):

    TARGET_URL = "https://api.elevenlabs.io/v1/convai/conversations"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()



@app.get("/detail-conversation/{conversation_id}")
def get_detail_conversation(conversation_id: str , apikey: str = Header(...)):

    TARGET_URL = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}"

    headers = {
        "Content-Type": "application/json",
        'xi-api-key'  : apikey
    }
    
    response = requests.get(TARGET_URL, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return response.json()






@app.delete("/agent/{agent_id}")
def delete_agent(agent_id: str , apikey: str = Header(...)):
    url = f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}"
    headers = {
        'xi-api-key'  : apikey,
        "Content-Type": "application/json"
    }
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    
    return {"message": "Agent deleted successfully"}
