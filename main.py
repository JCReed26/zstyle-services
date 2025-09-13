from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database.database import connect_to_mongo, close_mongo_connection
from routers.users import router as users_router
from routers.client_to_agent import router as client_toAgent_router
from fastapi.middleware.cors import CORSMiddleware

import logging
import os

# Initialize logging with Google Cloud fallback
logger = logging.getLogger("agent-connect-server.main")
logger.setLevel(logging.INFO)

# Try to initialize Google Cloud Logging, fall back to standard logging
try:
    from google.cloud.logging import Client
    from google.cloud.logging.handlers import CloudLoggingHandler
    
    logging_client = Client()
    handler = CloudLoggingHandler(logging_client)
    logger.addHandler(handler)
    logger.info("Google Cloud Logging initialized successfully for main")
except Exception as e:
    # Fallback to standard logging for local development
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.warning(f"Using standard logging for main (Google Cloud Logging unavailable): {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Starting MongoDB Connect ...")
    await connect_to_mongo()
    logger.info("MongoDB Connected Successfully")
    yield
    # On shutdown
    logging.info("Closing MongoDB Connection ...")
    await close_mongo_connection()
    logger.info("MongoDB Connection Closed Successfully")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(client_toAgent_router)

app.mount("/static", StaticFiles(directory="dashboards"), name="static")

@app.get("/")
async def check_health():
    logger.info("Health check requested")
    return {"Hello World!": "You Suck At Programming"}
