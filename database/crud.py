from .database import get_user_collection
from bson.objectid import ObjectId
from .schema import User, UserCreate
from auth import get_password_hash

async def create_new_user(newUser: UserCreate):
    collection = get_user_collection()
    if collection is None:
        return None

    hashed_password = get_password_hash(newUser.password)

    user_doc = newUser.model_dump()
    user_doc["hashed_password"] = hashed_password
    del user_doc["password"]

    result = await collection.insert_one(user_doc)
    if result.inserted_id:
        # Retrieve the newly created user to ensure all fields are correctly populated, including the MongoDB-generated _id
        created_user_from_db = await collection.find_one({"_id": result.inserted_id})
        if created_user_from_db:
            created_user_from_db["id"] = str(created_user_from_db["_id"])
            del created_user_from_db["_id"]
            return User(**created_user_from_db)
    return None

async def get_user_by_email(email: str):
    collection = get_user_collection()
    if collection is None:
        return None
    user_by_email = await collection.find_one({"email": email})
    if user_by_email:
        # Map MongoDB's _id to id for the returned User object
        user_by_email["id"] = str(user_by_email['_id'])
        del user_by_email['_id']
    return user_by_email

async def get_all_users():
    collection = get_user_collection()
    if collection is None:
        return []
    users = await collection.find().to_list(length=100)
    for user in users:
        if '_id' in user:
            user["id"] = str(user['_id'])
            del user['_id']
    return users

async def get_user_by_phone_number(phone_number: str):
    collection = get_user_collection()
    if collection is None:
        return None
    user_by_phone = await collection.find_one({"phone_number": phone_number})
    if user_by_phone:
        user_by_phone["id"] = str(user_by_phone['_id'])
        del user_by_phone['_id']
    return user_by_phone

from bson.objectid import ObjectId

async def get_user_by_id(id: str):
    collection = get_user_collection()
    if collection is None:
        return None
    try:
        user = await collection.find_one({"_id": ObjectId(id)})
    except Exception:
        return None
    
    if user:
        user["id"] = str(user['_id'])
        del user['_id']
    return user

async def delete_user(id: str):
    collection = get_user_collection()
    if collection is None:
        return False
    result = await collection.delete_one({"_id": ObjectId(id)})
    return result.deleted_count > 0