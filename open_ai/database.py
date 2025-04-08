from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import supabase


load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")
DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}"
Engine = create_engine(DATABASE_URL)



SUPABASE_KEY = os.getenv("APIKEY_SECRET")
SUPABASE_URL = os.getenv("SUPABASE_URL")
Client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
Sensionalocal = sessionmaker(bind=Engine, autoflush=False, autocommit=False)

Base = declarative_base()
