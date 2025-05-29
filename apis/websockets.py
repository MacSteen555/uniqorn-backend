import json
import asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from agents.research import create_research_agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")

manager = ConnectionManager()

# Callback handler for streaming responses
class WebSocketCallbackHandler(BaseCallbackHandler):
    def __init__(self, client_id: str, loop: asyncio.AbstractEventLoop):
        self.client_id = client_id
        self.loop = loop
        
    def on_llm_new_token(self, token: str, **kwargs):
        coro = manager.send_message(json.dumps({
            "type": "token",
            "content": token
        }), self.client_id)
        asyncio.run_coroutine_threadsafe(coro, self.loop)
        
    def on_tool_start(self, serialized: Dict[str, any], input_str: str, **kwargs):
        tool_name = serialized.get("name", "Unknown tool")
        coro = manager.send_message(json.dumps({
            "type": "tool_start",
            "tool": tool_name,
            "input": input_str
        }), self.client_id)
        asyncio.run_coroutine_threadsafe(coro, self.loop)
        
    def on_tool_end(self, output: str, **kwargs):
        coro = manager.send_message(json.dumps({
            "type": "tool_end",
            "output": output
        }), self.client_id)
        asyncio.run_coroutine_threadsafe(coro, self.loop)

@app.websocket("/ws/research/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    
    conversation_history_dicts: List[Dict[str, str]] = []
    current_loop = asyncio.get_running_loop()
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "query":
                    callback_handler = WebSocketCallbackHandler(client_id, current_loop)
                    agent = create_research_agent(
                        streaming=True,
                        callbacks=[callback_handler]
                    )
                    
                    await manager.send_message(json.dumps({
                        "type": "start",
                        "message": "Starting research..."
                    }), client_id)
                    
                    query = message.get("query", "")
                    conversation_history_dicts.append({"role": "user", "content": query})
                    
                    asyncio.create_task(run_agent(agent, query, client_id, conversation_history_dicts))
                    
            except json.JSONDecodeError:
                await manager.send_message(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }), client_id)
            except Exception as e:
                print(f"Error processing message for {client_id}: {e}")
                await manager.send_message(json.dumps({
                    "type": "error",
                    "message": f"An error occurred: {str(e)}"
                }), client_id)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for client: {client_id}")
    except Exception as e:
        print(f"Unexpected error in websocket_endpoint for {client_id}: {e}")
    finally:
        manager.disconnect(client_id)
        print(f"Cleaned up connection for client: {client_id}")

async def run_agent(agent, current_query: str, client_id: str, conversation_history_dicts: List[Dict[str, str]]):
    try:
        langchain_chat_history: List[BaseMessage] = []
        if len(conversation_history_dicts) > 1:
            for msg_dict in conversation_history_dicts[:-1]:
                if msg_dict["role"] == "user":
                    langchain_chat_history.append(HumanMessage(content=msg_dict["content"]))
                elif msg_dict["role"] == "assistant":
                    langchain_chat_history.append(AIMessage(content=msg_dict["content"]))

        agent_input = {
            "input": current_query,
            "chat_history": langchain_chat_history
        }
        
        result = await asyncio.to_thread(agent.invoke, agent_input)
        
        output = result.get("output", "")
        
        conversation_history_dicts.append({"role": "assistant", "content": output})
        
        await manager.send_message(json.dumps({
            "type": "complete",
            "result": output
        }), client_id)
    except Exception as e:
        print(f"Error in agent execution for {client_id}: {e}")
        import traceback
        traceback.print_exc()
        await manager.send_message(json.dumps({
            "type": "error",
            "message": f"Error during research: {str(e)}"
        }), client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)