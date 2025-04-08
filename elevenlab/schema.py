from pydantic import BaseModel

class Prompt(BaseModel):
    prompt: str
    llm: str

class Agent(BaseModel):
    first_message: str
    language: str
    prompt: Prompt

class Conversation(BaseModel):
    max_duration_seconds: int

class Tts(BaseModel):
    model_id: str
    agent_output_audio_format: str

class Turn(BaseModel):
    turn_timeout: int

class Asr(BaseModel):
    quality: str
    provider: str
    user_input_audio_format: str

class ConversationConfig(BaseModel):
    asr: Asr
    turn: Turn
    tts: Tts
    conversation: Conversation
    agent: Agent

class CreateAgentRequest(BaseModel):
    conversation_config: ConversationConfig


