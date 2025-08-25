import json
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_calls.chatbot import LandingChatbot
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    web_search: Optional[bool] = False

class ChatResponse(BaseModel):
    response: str
    session_id: str
    web_search_used: bool

class StreamEvent(BaseModel):
    type: str
    content: Optional[str] = None
    tool: Optional[str] = None
    arguments: Optional[Dict] = None
    output: Optional[str] = None
    new_agent: Optional[str] = None
    timestamp: float
    web_search_used: bool

# Initialize the chatbot agent
chatbot_agent = LandingChatbot()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Simple chat endpoint that returns the complete response.
    """
    try:
        web_search = request.web_search or False
        response = await chatbot_agent.run_simple(request.message, web_search=web_search)
        return ChatResponse(
            response=response,
            session_id=request.session_id or "default",
            web_search_used=web_search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint that returns events as they happen.
    """
    async def generate_stream():
        try:
            web_search = request.web_search or False
            async for event in chatbot_agent.stream_research(request.message, web_search=web_search):
                # Convert event to JSON and send as Server-Sent Events
                event_data = StreamEvent(
                    type=event["type"],
                    content=event.get("content"),
                    tool=event.get("tool"),
                    arguments=event.get("arguments"),
                    output=event.get("output"),
                    new_agent=event.get("new_agent"),
                    timestamp=event["timestamp"],
                    web_search_used=web_search
                )
                
                yield f"data: {event_data.model_dump_json()}\n\n"
                
        except Exception as e:
            web_search = request.web_search or False
            error_event = StreamEvent(
                type="error",
                content=f"Streaming error: {str(e)}",
                timestamp=asyncio.get_event_loop().time(),
                web_search_used=web_search
            )
            yield f"data: {error_event.model_dump_json()}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chatbot-api"}

@app.get("/")
async def root():
    return {
        "message": "Chatbot API",
        "endpoints": {
            "POST /chat": "Simple chat (returns complete response)",
            "POST /chat/stream": "Streaming chat (Server-Sent Events)",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 