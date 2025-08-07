import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()

class DB:
    client: AsyncMongoClient = None

db = DB()

async def connect_to_mongo():
    uri = os.getenv("MONGO_DB_URI")
    print("Connecting to MongoDB...")
    try:
        db.client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        await db.client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except ServerSelectionTimeoutError as e:
        print(f"Could not connect to MongoDB: {e}")
        db.client = None
    except Exception as e:
        print(f"An error occurred: {e}")
        db.client = None

async def close_mongo_connection():
    if db.client:
        await db.client.close()
        print("MongoDB connection closed.")

def get_user_collection():
    if db.client:
        return db.client['UserDatabase']['UserData']
    return None
