from fastapi import FastAPI
from gemini.endpoints import router as gemini_router
from open_ai.endpoints import router as chatgpt_router
from elevenlab.endpoints import router as elevenlabs_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.include_router(gemini_router, prefix="/gemini")
app.include_router(chatgpt_router, prefix="/chatgpt")
app.include_router(elevenlabs_router, prefix="/elevenlabs")
