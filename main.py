import json
import asyncio
import uuid
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from apis.roadmap import router as roadmap_router
from apis.landscape import router as landscape_router
from apis.context import router as context_router
from agent_calls.chatbot import LandingChatbot
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

# Initialize chatbot components
chatbot_agent = LandingChatbot()

class Message:
    """Represents a chat message with metadata."""
    def __init__(self, role: str, content: str, message_id: Optional[str] = None):
        self.id = message_id or str(uuid.uuid4())
        self.role = role
        self.content = content
        self.timestamp = asyncio.get_event_loop().time()
        self.index = 0  # Will be set by ChatSession

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "index": self.index
        }

class ChatSession:
    """Manages a single chat session with enhanced state management."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Message] = []
        self.is_generating = False
        self.current_task: Optional[asyncio.Task] = None
        self.interruption_requested = False
        self._lock = asyncio.Lock()
    
    def add_message(self, role: str, content: str, message_id: Optional[str] = None) -> Message:
        """Add a new message to the conversation."""
        message = Message(role, content, message_id)
        message.index = len(self.messages)
        self.messages.append(message)
        return message
    
    def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """Get a message by its ID."""
        for message in self.messages:
            if message.id == message_id:
                return message
        return None
    
    def get_message_by_index(self, index: int) -> Optional[Message]:
        """Get message by index."""
        if 0 <= index < len(self.messages):
            return self.messages[index]
        return None
    
    def reset_to_message(self, reset_point: int) -> bool:
        """Reset chat history to a specific message index."""
        if 0 <= reset_point < len(self.messages):
            self.messages = self.messages[:reset_point + 1]
            return True
        return False
    
    def clear_history(self):
        """Clear all messages."""
        self.messages = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history as a list of dictionaries."""
        return [msg.to_dict() for msg in self.messages]
    
    async def request_interruption(self):
        """Request interruption of current generation."""
        async with self._lock:
            self.interruption_requested = True
            if self.current_task and not self.current_task.done():
                self.current_task.cancel()
    
    def is_interrupted(self) -> bool:
        """Check if interruption was requested."""
        return self.interruption_requested
    
    def reset_interruption_state(self):
        """Reset interruption state."""
        self.interruption_requested = False

# WebSocket connection manager for chat sessions
class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_sessions: Dict[str, ChatSession] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if session_id not in self.chat_sessions:
            self.chat_sessions[session_id] = ChatSession(session_id)
        logger.info(f"Client connected to chatbot websocket: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.chat_sessions:
            # Cancel any ongoing generation
            session = self.chat_sessions[session_id]
            if session.current_task and not session.current_task.done():
                session.current_task.cancel()
            del self.chat_sessions[session_id]
        logger.info(f"Client disconnected from chatbot websocket: {session_id}")

    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        return self.chat_sessions.get(session_id)

    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send a message to a specific client."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                # Remove the connection if it's broken
                self.disconnect(session_id)

manager = ChatConnectionManager()

# Include your routers
app.include_router(roadmap_router, prefix="/api", tags=["roadmap"])
app.include_router(landscape_router, prefix="/api", tags=["landscape"])
app.include_router(context_router, prefix="/api", tags=["context"])

async def handle_message_generation(websocket: WebSocket, session_id: str, user_input: str, web_search: bool = False):
    """Handle message generation with interruption support and session-based memory."""
    session = manager.get_chat_session(session_id)
    if not session:
        return
    
    # Add user message to history
    user_message = session.add_message("user", user_input)
    
    # Send user message confirmation
    await manager.send_message(session_id, {
        "type": "message_added",
        "message": user_message.to_dict(),
        "timestamp": asyncio.get_event_loop().time()
    })
    
    # Set generation state
    session.is_generating = True
    session.reset_interruption_state()
    
    try:
        # Create generation task using session-based memory
        async def generate_response():
            full_response = ""
            async for event in chatbot_agent.stream_research(session_id, user_input, web_search=web_search):
                # Check for interruption
                if session.is_interrupted():
                    logger.info(f"Generation interrupted for session {session_id}")
                    return
                
                if event["type"] == "chunk":
                    full_response += event["content"]
                    await manager.send_message(session_id, {
                        "type": "chunk",
                        "content": event["content"],
                        "timestamp": event["timestamp"]
                    })
                elif event["type"] == "tool_call":
                    await manager.send_message(session_id, {
                        "type": "tool_call",
                        "tool": event["tool"],
                        "arguments": event["arguments"],
                        "timestamp": event["timestamp"]
                    })
                elif event["type"] == "tool_output":
                    await manager.send_message(session_id, {
                        "type": "tool_output",
                        "output": event["output"],
                        "timestamp": event["timestamp"]
                    })
                elif event["type"] == "agent_updated":
                    await manager.send_message(session_id, {
                        "type": "agent_updated",
                        "new_agent": event["new_agent"],
                        "timestamp": event["timestamp"]
                    })
                elif event["type"] == "message_complete":
                    await manager.send_message(session_id, {
                        "type": "message_complete",
                        "timestamp": event["timestamp"]
                    })
            
            # Add assistant response to history if not interrupted
            if full_response and not session.is_interrupted():
                assistant_message = session.add_message("assistant", full_response)
                # Also add to chatbot's conversation memory
                chatbot_agent.add_assistant_response(session_id, full_response)
                await manager.send_message(session_id, {
                    "type": "message_added",
                    "message": assistant_message.to_dict(),
                    "timestamp": asyncio.get_event_loop().time()
                })
        
        # Start generation task
        session.current_task = asyncio.create_task(generate_response())
        await session.current_task
        
    except asyncio.CancelledError:
        logger.info(f"Generation task cancelled for session {session_id}")
        await manager.send_message(session_id, {
            "type": "interrupted",
            "message": "Response generation was interrupted",
            "timestamp": asyncio.get_event_loop().time()
        })
    except Exception as e:
        logger.error(f"Error during message generation for {session_id}: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "content": f"Generation error: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        })
    finally:
        session.is_generating = False
        session.current_task = None

# Add WebSocket endpoint
@app.websocket("/ws/chatbot/{session_id}")
async def chatbot_websocket(websocket: WebSocket, session_id: str):
    """Handle WebSocket connections for the chatbot with enhanced features."""
    await manager.connect(websocket, session_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_message(session_id, {
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to chatbot",
            "timestamp": asyncio.get_event_loop().time()
        })
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type")
            
            session = manager.get_chat_session(session_id)
            if not session:
                logger.error(f"No session found for {session_id}")
                break
            
            if message_type == "message":
                user_input = message.get("content", "")
                web_search = message.get("web_search", False)
                
                # Start message generation
                await handle_message_generation(websocket, session_id, user_input, web_search)
                
            elif message_type == "interrupt":
                # Handle response interruption
                logger.info(f"Interruption requested for session {session_id}")
                await session.request_interruption()
                await manager.send_message(session_id, {
                    "type": "interruption_requested",
                    "message": "Interruption request received",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            elif message_type == "reset_to_message":
                # Handle chat reset to specific point
                reset_point = message.get("reset_point")
                if reset_point is not None:
                    if session.reset_to_message(reset_point):
                        # Clear chatbot memory and rebuild it from the reset point
                        chatbot_agent.clear_session_memory(session_id)
                        
                        # Rebuild chatbot memory from the remaining messages
                        for msg in session.messages:
                            if msg.role == "user":
                                chatbot_agent._get_or_create_memory(session_id).add_message("user", msg.content)
                            elif msg.role == "assistant":
                                chatbot_agent._get_or_create_memory(session_id).add_message("assistant", msg.content)
                        
                        await manager.send_message(session_id, {
                            "type": "reset_to_message",
                            "reset_point": reset_point,
                            "history": session.get_history(),
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    else:
                        await manager.send_message(session_id, {
                            "type": "error",
                            "content": f"Invalid reset point: {reset_point}",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                else:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "content": "Invalid reset_to_message request: missing reset_point",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                
            elif message_type == "clear_history":
                # Clear chat history
                session.clear_history()
                # Also clear the chatbot's session memory
                chatbot_agent.clear_session_memory(session_id)
                await manager.send_message(session_id, {
                    "type": "history_cleared",
                    "message": "Chat history cleared",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            elif message_type == "get_history":
                # Send current chat history
                await manager.send_message(session_id, {
                    "type": "history",
                    "history": session.get_history(),
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            elif message_type == "get_session_info":
                # Send session information including chatbot memory status
                session_info = chatbot_agent.get_session_info(session_id)
                await manager.send_message(session_id, {
                    "type": "session_info",
                    "session_info": session_info,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            elif message_type == "ping":
                # Respond to ping
                await manager.send_message(session_id, {
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
            else:
                # Unknown message type
                await manager.send_message(session_id, {
                    "type": "error",
                    "content": f"Unknown message type: {message_type}",
                    "timestamp": asyncio.get_event_loop().time()
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from chatbot websocket: {session_id}")
    except Exception as e:
        logger.error(f"Error in chatbot websocket for {session_id}: {e}")
        await manager.send_message(session_id, {
            "type": "error",
            "content": f"WebSocket error: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        })
    finally:
        manager.disconnect(session_id)

# Add health check endpoint for chatbot
@app.get("/chatbot/health")
async def chatbot_health_check():
    return {"status": "healthy", "service": "chatbot-websocket"}

# Add chat history endpoint for debugging
@app.get("/chatbot/history/{session_id}")
async def get_chatbot_history(session_id: str):
    session = manager.get_chat_session(session_id)
    if session:
        return {
            "session_id": session_id,
            "history": session.get_history(),
            "message_count": len(session.messages),
            "is_generating": session.is_generating
        }
    else:
        return {"error": "Session not found"}

@app.get("/")
async def root():
    return {"message": "Uniqorn Backend API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
