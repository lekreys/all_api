from pydantic import BaseModel




class Conversation(BaseModel):

    id_conversation : str
    user_message: str
    agent_message : str
    input_token : int
    output_token : int
    total_token : int
    transcript : str

    class Config:
        orm_mode = True
