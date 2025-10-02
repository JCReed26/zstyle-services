import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError

import logging

# Initialize logging with Google Cloud fallback
logger = logging.getLogger("agent-connect-server.database")
logger.setLevel(logging.INFO)

# Try to initialize Google Cloud Logging, fall back to standard logging
try:
    from google.cloud.logging import Client
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    logging_client = Client()
    handler = CloudLoggingHandler(logging_client)
    logger.addHandler(handler)
    logger.info("Google Cloud Logging initialized successfully for database")
except Exception as e:
    # Fallback to standard logging for local development
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.warning(f"Using standard logging for database (Google Cloud Logging unavailable): {e}")


load_dotenv()

class DB:
    client: AsyncMongoClient = None

db = DB()

async def connect_to_mongo():
    uri = os.getenv("MONGO_DB_URI")
    logger.info("Connecting to MongoDB...")
    try:
        db.client = AsyncMongoClient(uri, serverSelectionTimeoutMS=5000)
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
    except ServerSelectionTimeoutError as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        db.client = None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        db.client = None

async def close_mongo_connection():
    if db.client:
        await db.client.close()
        logger.info("MongoDB connection closed.")

def get_user_collection():
    if db.client:
        return db.client['diverge']['users']
    return None
