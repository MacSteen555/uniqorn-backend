import json
import asyncio
import uuid
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from apis.roadmap import router as roadmap_router
from apis.landscape import router as landscape_router
from apis.context import router as context_router
from apis.chatbot_api import router as chatbot_router
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Uniqorn Backend API",
    description="Backend API for roadmap generation and chat functionality",
    version="1.0.0"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routers
app.include_router(roadmap_router, prefix="/api", tags=["roadmap"])
app.include_router(landscape_router, prefix="/api", tags=["landscape"])
app.include_router(context_router, prefix="/api", tags=["context"])
app.include_router(chatbot_router, tags=["chatbot"])

@app.get("/")
async def root():
    return {"message": "Uniqorn Backend API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
