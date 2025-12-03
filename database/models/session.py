from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
import uuid
from database.sqlite_db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, unique=True, nullable=False)  # ADK session ID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    session_data = Column(JSON, nullable=True)  # Stores session state
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())