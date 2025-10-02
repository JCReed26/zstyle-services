from pydantic import BaseModel, EmailStr, Field
from uuid import UUID, uuid4
from typing import Optional
from bson.objectid import ObjectId

class User(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    email: str
    hashed_password: str
    phone_number: str
    username: str

    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str
        }

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    phone_number: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str