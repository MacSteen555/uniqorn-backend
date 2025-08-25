import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from dotenv import load_dotenv
from agent_calls.chatbot import LandingChatbot

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

# WebSocket connection manager for chat sessions
class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_histories: Dict[str, List[Dict[str, Union[str, float]]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = []

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.chat_histories:
            del self.chat_histories[session_id]

    def get_chat_history(self, session_id: str) -> List[Dict[str, Union[str, float]]]:
        return self.chat_histories.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = []
        self.chat_histories[session_id].append({
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time()
        })

    def clear_history(self, session_id: str):
        if session_id in self.chat_histories:
            self.chat_histories[session_id] = []

manager = ChatConnectionManager()
chatbot_agent = LandingChatbot()

@app.websocket("/ws/chatbot/{session_id}")
async def chatbot_websocket(websocket: WebSocket, session_id: str):
    """Handle WebSocket connections for the chatbot with streaming and chat history."""
    await manager.connect(websocket, session_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to chatbot",
            "timestamp": asyncio.get_event_loop().time()
        }))
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "message":
                user_input = message.get("content", "")
                web_search = message.get("web_search", False)
                
                # Add user message to chat history
                manager.add_message(session_id, "user", user_input)
                
                # Send acknowledgment
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "content": "Processing your message...",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
                # Stream the response using the chatbot agent
                full_response = ""
                async for event in chatbot_agent.stream_research(user_input, user_prompt=user_input, web_search=web_search):
                    if event["type"] == "chunk":
                        full_response += event["content"]
                        await websocket.send_text(json.dumps({
                            "type": "chunk",
                            "content": event["content"],
                            "timestamp": event["timestamp"]
                        }))
                    elif event["type"] == "tool_call":
                        await websocket.send_text(json.dumps({
                            "type": "tool_call",
                            "tool": event["tool"],
                            "arguments": event["arguments"],
                            "timestamp": event["timestamp"]
                        }))
                    elif event["type"] == "tool_output":
                        await websocket.send_text(json.dumps({
                            "type": "tool_output",
                            "output": event["output"],
                            "timestamp": event["timestamp"]
                        }))
                    elif event["type"] == "agent_updated":
                        await websocket.send_text(json.dumps({
                            "type": "agent_updated",
                            "new_agent": event["new_agent"],
                            "timestamp": event["timestamp"]
                        }))
                    elif event["type"] == "message_complete":
                        await websocket.send_text(json.dumps({
                            "type": "message_complete",
                            "timestamp": event["timestamp"]
                        }))
                
                # Add assistant response to chat history
                if full_response:
                    manager.add_message(session_id, "assistant", full_response)
                
                # Send completion signal
                await websocket.send_text(json.dumps({
                    "type": "complete",
                    "web_search_used": web_search,
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
            elif message.get("type") == "clear_history":
                # Clear chat history
                manager.clear_history(session_id)
                await websocket.send_text(json.dumps({
                    "type": "history_cleared",
                    "message": "Chat history cleared",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
            elif message.get("type") == "get_history":
                # Send current chat history
                chat_history = manager.get_chat_history(session_id)
                await websocket.send_text(json.dumps({
                    "type": "chat_history",
                    "history": chat_history,
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
            elif message.get("type") == "ping":
                # Respond to ping
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                }))
                
    except WebSocketDisconnect:
        print(f"Client disconnected from chatbot websocket: {session_id}")
    except Exception as e:
        print(f"Error in chatbot websocket for {session_id}: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": f"WebSocket error: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }))
    finally:
        manager.disconnect(session_id)
        print(f"Cleaned up chatbot connection for session: {session_id}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chatbot-websocket"}

# Get chat history endpoint (for debugging)
@app.get("/chat-history/{session_id}")
async def get_chat_history(session_id: str):
    history = manager.get_chat_history(session_id)
    return {
        "session_id": session_id,
        "history": history,
        "message_count": len(history)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 