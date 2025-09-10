"""User Data Passage + CRUD"""

from fastapi import APIRouter, HTTPException, status
from database.crud import create_new_user, get_user_by_email, get_all_users, get_user_by_id, delete_user
from database.schema import User, UserCreate, UserLogin
from auth import verify_password
from typing import List
import logging
from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler

logging_client = Client()
handler = CloudLoggingHandler(logging_client)
logger = logging.getLogger("agent-connect-server.users")
logger.setLevel(logging.INFO)
logger.addHandler(handler)


router = APIRouter(prefix="/user")

@router.post("/new_user/", response_model=User, status_code=status.HTTP_201_CREATED)
async def add_new_user_endpt(user: UserCreate):
    """
    Creates a new user in the database.
    """
    # Check if user already exists
    logger.info(f"******creating a new user: {user}")
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    created_user = await create_new_user(user)
    if created_user:
        created_user['_id'] = str(created_user['_id'])
        return created_user
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user."
        )

# AI Generated CRAP - rewrite using FastAPI built in capabilities 
# JIMMY START FUCKING LOCKING IN ON YOUR CODE AND USE THE DOCS 
# SCALABLE CLEAN QUALITY SOFTWARE 
@router.post("/login", response_model=User)
async def login_for_access_token(form_data: UserLogin):
    """
    Logs in a user and returns user data.
    """
    user = await get_user_by_email(form_data.email)
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user['_id'] = str(user['_id'])
    return User(**user)


@router.get("/all_users", response_model=List[User])
async def get_all_users_endpt():
    """
    Retrieves all users.
    """
    users = await get_all_users()
    # No need to check if users exist, an empty list is a valid response.
    for user in users:
        user['_id'] = str(user['_id'])
    return users

@router.get("/{userid}", response_model=User)
async def get_user_by_id_endpt(userid: str):
    """
    Retrieves a user by their unique userid.
    """
    user = await get_user_by_id(userid)
    if user:
        user['_id'] = str(user['_id'])
        return user
    raise HTTPException(status_code=404, detail="User not found")
