from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
import uuid
from database.sqlite_db import Base

def generate_uuid():
    return str(uuid.uuid4())

class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    config_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())