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
        # Retrieve the newly created user to ensure all fields are correctly populated
        created_user_from_db = await collection.find_one({"_id": result.inserted_id})
        if created_user_from_db:
            # Let Pydantic handle the _id to id mapping
            return User(**created_user_from_db)
    return None

async def get_user_by_email(email: str):
    collection = get_user_collection()
    if collection is None:
        return None
    # Return the raw document, Pydantic will handle the _id mapping
    return await collection.find_one({"email": email})

async def get_all_users():
    collection = get_user_collection()
    if collection is None:
        return []
    # Pydantic will handle the _id mapping for each user in the list
    return await collection.find().to_list(length=100)

async def get_user_by_phone_number(phone_number: str):
    collection = get_user_collection()
    if collection is None:
        return None
    # Return the raw document, Pydantic will handle the _id mapping
    return await collection.find_one({"phone_number": phone_number})

async def get_user_by_id(id: str):
    collection = get_user_collection()
    if collection is None:
        return None
    try:
        # Return the raw document, Pydantic will handle the _id mapping
        return await collection.find_one({"_id": ObjectId(id)})
    except Exception:
        return None

async def delete_user(id: str):
    collection = get_user_collection()
    if collection is None:
        return False
    result = await collection.delete_one({"_id": ObjectId(id)})
    return result.deleted_count > 0