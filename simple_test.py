import asyncio
import websockets
import json
import uuid
import sys
from datetime import datetime

SERVER_URL = "ws://localhost:8000/ws/chatbot" # no domain, test script
SESSION_ID = "cli-test-fixed-session" # fixed session ID

async def receive_messages(websocket):
    """Listen for messages from the server."""
    try:
        async for message in websocket:

            data = json.loads(message) # parse JSON
            msg_type = data.get("type")
            
            if msg_type == "connected":

                print(f"\n✅ Connected! Session ID: {data['session_id']}\n")
                print("Type your message and press Enter (or 'quit' to exit):")
                print("> ", end="", flush=True)
                
            elif msg_type == "chunk":
                print(data.get("content", ""), end="", flush=True) # Stream content
                
            elif msg_type == "message_complete":
                print("\n\n> ", end="", flush=True)
                
            elif msg_type == "tool_call":
                tool_name = data.get("tool", "unknown")
                args = data.get("arguments", {})
                print(f"\n[🛠️ Tool Call: {tool_name}]", flush=True)
                
            elif msg_type == "tool_output":
                print(f"[📊 Tool Output Received]", flush=True)
                
            elif msg_type == "error":
                print(f"\n❌ Error: {data.get('content')}")
                print("\n> ", end="", flush=True)
                
            elif msg_type == "message_added": # user message
                pass # ignore

    except websockets.exceptions.ConnectionClosed:
        print("\nConnection closed by server.")

async def send_messages(websocket):
    """Read input from stdin and send to server."""
    loop = asyncio.get_event_loop()
    while True:
        # using run_in_executor to avoid blocking the loop
        user_input = await loop.run_in_executor(None, input)
        
        if user_input.lower() in ["quit", "exit"]: # commands to close socket
            print("Closing socket...")
            await websocket.close()
            break
            
        if user_input.strip():
            message = {
                "type": "message",
                "content": user_input,
                "web_search": True # keep web search enabled for now (cost save option)
            }

            await websocket.send(json.dumps(message))

async def main():

    uri = f"{SERVER_URL}/{SESSION_ID}"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # Run receive and send loops concurrently
            receiver = asyncio.create_task(receive_messages(websocket))
            sender = asyncio.create_task(send_messages(websocket))
            
            done, pending = await asyncio.wait( # wait for finish
                [receiver, sender], # either side can close socket
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                
    except ConnectionRefusedError:
        print("❌ Could not connect to server. Is it running?")
        print("Run: python main.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")