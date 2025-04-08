from open_ai.database import Base
from sqlalchemy import Column, String, Integer, TIMESTAMP

class Conversation(Base):

    __tablename__ = "Conversation"

    id = Column(Integer, primary_key=True, index=True)
    id_conversation = Column(String)
    user_message = Column(String , nullable=True)
    agent_message = Column(String)
    timestamp = Column(TIMESTAMP)
    input_token = Column(Integer)
    output_token = Column(Integer)
    total_token = Column(Integer)
    transcript = Column(String)


    
