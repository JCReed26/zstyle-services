import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from database.database import connect_to_mongo, close_mongo_connection
from routers.users import router as users_router
from routers.client_to_agent import router as client_toAgent_router
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format='%(levelname)s:\t  %(name)s:%(message)s')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    await connect_to_mongo()
    yield
    # On shutdown
    await close_mongo_connection()

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
    return {"Hello World!": "You Suck At Programming"}
