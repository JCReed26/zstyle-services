from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
import uuid
from database.sqlite_db import Base

def generate_uuid():
    return str(uuid.uuid4())

class Credential(Base):
    __tablename__ = "credentials"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    service_name = Column(String, nullable=False)  # e.g., 'ticktick', 'google_calendar'
    credential_data = Column(JSON, nullable=True)  # Stores encrypted tokens, etc.
    encrypted_token = Column(String, nullable=True)  # For frequently accessed tokens
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())