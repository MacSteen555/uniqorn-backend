import os
import asyncio
import json
from typing import List, Optional, Any, Dict, AsyncGenerator
from pathlib import Path
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, WebSearchTool, Runner
from agents.model_settings import ModelSettings
from dotenv import load_dotenv
from datetime import datetime

from tools.newsapi import news_search
from tools.producthunt import get_producthunt_categories, get_producthunt_search_type_help, producthunt_search
from tools.pytrends import trends_get
from tools.reddit import reddit_search
from utils.prompt import load_prompt

load_dotenv()

def serialize_tool_output(output: Any) -> str:
    """
    Serialize tool output to JSON string, handling Pydantic models and datetime objects.
    
    Args:
        output: The tool output to serialize
        
    Returns:
        str: JSON serialized output
    """
    try:
        # If it's a Pydantic model, convert to dict first
        if hasattr(output, 'model_dump'):
            output = output.model_dump()
        elif hasattr(output, 'dict'):
            output = output.dict()
        
        # Handle datetime objects in the output
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(output, default=json_serializer, ensure_ascii=False)
    except Exception as e:
        # Fallback: convert to string representation
        return str(output)

class ConversationMemory:
    """Manages conversation memory for a session with token-aware truncation."""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.messages: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        self.messages.append(message)
        self._truncate_if_needed()
    
    def _truncate_if_needed(self):
        """Truncate conversation if it exceeds token limit."""
        # Simple token estimation (roughly 4 chars per token)
        total_chars = sum(len(msg["content"]) for msg in self.messages)
        estimated_tokens = total_chars // 4
        
        if estimated_tokens > self.max_tokens:
            # Remove oldest messages, keeping recent ones
            while estimated_tokens > self.max_tokens and len(self.messages) > 2:
                removed = self.messages.pop(0)  # Remove oldest message
                total_chars -= len(removed["content"])
                estimated_tokens = total_chars // 4
    
    def get_conversation(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.messages.copy()
    
    def clear(self):
        """Clear conversation history."""
        self.messages = []
    
    def reset_to_message(self, message_index: int):
        """Reset conversation to a specific message index."""
        if 0 <= message_index < len(self.messages):
            self.messages = self.messages[:message_index + 1]
            return True
        return False

class LandingChatbot:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "chatbot.yaml"
        self.system_prompt = load_prompt(self.prompt_path, "chatbot_system")
        
        # Available tools
        self.available_tools = [
            WebSearchTool(search_context_size="medium"),
            news_search,
            trends_get
        ]
        
        # Store conversation memory per session
        self.session_memory: Dict[str, ConversationMemory] = {}

    def _get_or_create_memory(self, session_id: str) -> ConversationMemory:
        """Get or create conversation memory for a session."""
        if session_id not in self.session_memory:
            self.session_memory[session_id] = ConversationMemory()
        return self.session_memory[session_id]

    def _create_agent(self, web_search: bool = False) -> Agent:
        """Create agent with specified settings."""
        # Configure model settings
        tool_choice = "required" if web_search else "auto"
        
        model_settings = ModelSettings(
            temperature=0.7,
            max_tokens=12000,
            tool_choice=tool_choice,
            parallel_tool_calls=True,
        )

        # Create the agent using OpenAI Agents SDK with all tools
        agent = Agent(
            name="Startup Research Chatbot",
            model="gpt-4.1",
            instructions=self.system_prompt,
            tools=self.available_tools,
            model_settings=model_settings,
        )
        
        return agent

    def _format_conversation_context(self, memory: ConversationMemory) -> str:
        """Format conversation history for the agent."""
        if not memory.messages:
            return ""
        
        formatted_history = "Previous conversation:\n"
        for msg in memory.messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if role in ['user', 'assistant']:
                formatted_history += f"{role.title()}: {content}\n"
        
        return formatted_history

    async def stream_research(self, session_id: str, user_prompt: str, web_search: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream research results using session-based memory.
        
        Args:
            session_id: Unique session identifier for memory
            user_prompt: The user's research question
            web_search: If True, forces tool usage by setting tool_choice to "required"
            
        Yields:
            Dict containing event type and data for streaming
        """
        # Get or create memory for this session
        memory = self._get_or_create_memory(session_id)
        
        # Add user message to memory
        memory.add_message("user", user_prompt)
        
        # Create agent with current settings
        agent = self._create_agent(web_search=web_search)
        
        # Format conversation history
        conversation_context = self._format_conversation_context(memory)
        
        # Combine context with current prompt
        if conversation_context:
            full_prompt = f"{conversation_context}\n\nCurrent message:\nUser: {user_prompt}"
        else:
            full_prompt = user_prompt
        
        # Use the agent with conversation context
        result = Runner.run_streamed(
            agent,
            input=full_prompt,
        )

        async for event in result.stream_events():
            # Handle raw response events for token-by-token streaming
            if event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                    yield {
                        "type": "chunk",
                        "content": event.data.delta,
                        "timestamp": asyncio.get_event_loop().time()
                    }
            
            # Handle run item events for tool calls and other updates
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    yield {
                        "type": "tool_call",
                        "tool": getattr(event.item, 'name', 'unknown'),
                        "arguments": getattr(event.item, 'arguments', {}),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                elif event.item.type == "tool_call_output_item":
                    # Serialize tool output to handle Pydantic models and datetime objects
                    serialized_output = serialize_tool_output(event.item.output)
                    yield {
                        "type": "tool_output",
                        "output": serialized_output,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                elif event.item.type == "message_output_item":
                    # Final message output
                    yield {
                        "type": "message_complete",
                        "timestamp": asyncio.get_event_loop().time()
                    }
            
            # Handle agent updates (e.g., handoffs)
            elif event.type == "agent_updated_stream_event":
                yield {
                    "type": "agent_updated",
                    "new_agent": event.new_agent.name,
                    "timestamp": asyncio.get_event_loop().time()
                }

    async def run_simple(self, session_id: str, user_prompt: str, web_search: bool = False) -> str:
        """
        Simple non-streaming version with session memory.
        
        Args:
            session_id: Unique session identifier for memory
            user_prompt: The user's research question
            web_search: If True, forces tool usage by setting tool_choice to "required"
            
        Returns:
            str: Complete response
        """
        # Get or create memory for this session
        memory = self._get_or_create_memory(session_id)
        
        # Add user message to memory
        memory.add_message("user", user_prompt)
        
        # Create agent with current settings
        agent = self._create_agent(web_search=web_search)
        
        # Format conversation history
        conversation_context = self._format_conversation_context(memory)
        
        # Combine context with current prompt
        if conversation_context:
            full_prompt = f"{conversation_context}\n\nCurrent message:\nUser: {user_prompt}"
        else:
            full_prompt = user_prompt
        
        # Use the agent with conversation context
        result = await Runner.run(agent, input=full_prompt)
        return result.final_output

    def add_assistant_response(self, session_id: str, response: str):
        """Add assistant response to conversation memory."""
        memory = self._get_or_create_memory(session_id)
        memory.add_message("assistant", response)

    def clear_session_memory(self, session_id: str):
        """Clear memory for a specific session."""
        if session_id in self.session_memory:
            del self.session_memory[session_id]

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session's memory usage."""
        if session_id in self.session_memory:
            memory = self.session_memory[session_id]
            return {
                "session_id": session_id,
                "has_memory": True,
                "message_count": len(memory.messages),
                "conversation": memory.get_conversation()
            }
        return {
            "session_id": session_id,
            "has_memory": False,
            "message_count": 0
        }

    def reset_session_to_message(self, session_id: str, message_index: int) -> bool:
        """Reset session memory to a specific message index."""
        if session_id in self.session_memory:
            memory = self.session_memory[session_id]
            return memory.reset_to_message(message_index)
        return False

    # Backward compatibility methods for existing code
    async def stream_research_legacy(self, user_prompt: str, conversation_history: Optional[List[Dict[str, Any]]] = None, web_search: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Legacy method for backward compatibility - creates a temporary session.
        """
        # Create a temporary session ID for legacy usage
        temp_session_id = f"legacy_{asyncio.get_event_loop().time()}"
        
        # If conversation history is provided, initialize memory
        if conversation_history:
            memory = self._get_or_create_memory(temp_session_id)
            for msg in conversation_history:
                memory.add_message(msg.get('role', 'user'), msg.get('content', ''))
        
        async for event in self.stream_research(temp_session_id, user_prompt, web_search):
            yield event
        # Clean up temporary session
        self.clear_session_memory(temp_session_id)

    async def run_simple_legacy(self, user_prompt: str, conversation_history: Optional[List[Dict[str, Any]]] = None, web_search: bool = False) -> str:
        """
        Legacy method for backward compatibility - creates a temporary session.
        """
        # Create a temporary session ID for legacy usage
        temp_session_id = f"legacy_{asyncio.get_event_loop().time()}"
        
        # If conversation history is provided, initialize memory
        if conversation_history:
            memory = self._get_or_create_memory(temp_session_id)
            for msg in conversation_history:
                memory.add_message(msg.get('role', 'user'), msg.get('content', ''))
        
        result = await self.run_simple(temp_session_id, user_prompt, web_search)
        # Clean up temporary session
        self.clear_session_memory(temp_session_id)
        return result

    
if __name__ == "__main__":
    async def test_streaming():
        """Test the streaming research agent with session memory."""
        agent = LandingChatbot()
        session_id = "test_session_123"
        
        test_inputs = [
            "I would like to build a startup that helps people learn to code, where should I start?",
            "What are the main challenges I should consider?",
            "Can you elaborate on the technical challenges?"
        ]
        
        print("🚀 Testing chatbot with session memory...")
        print("=" * 60)
        
        for i, test_input in enumerate(test_inputs, 1):
            print(f"\n📝 Message {i}: {test_input}")
            print("-" * 40)
            
            full_response = ""
            async for event in agent.stream_research(session_id, test_input, web_search=True):
                if event["type"] == "chunk":
                    full_response += event["content"]
                    print(event["content"], end="", flush=True)
                elif event["type"] == "tool_call":
                    print(f"\n🔧 Tool called: {event['tool']}")
                elif event["type"] == "tool_output":
                    print(f"📊 Tool output received")
                elif event["type"] == "agent_updated":
                    print(f"🤖 Agent switched to: {event['new_agent']}")
                elif event["type"] == "message_complete":
                    print("\n✅ Message complete!")
            
            # Add assistant response to memory
            agent.add_assistant_response(session_id, full_response)
            
            print(f"\n📊 Response length: {len(full_response)} characters")
        
        # Show session info
        session_info = agent.get_session_info(session_id)
        print(f"\n📋 Session Info: {session_info}")
        
        print("\n" + "=" * 60)
        print("✅ Research complete!")
    
    # Run the test
    asyncio.run(test_streaming())
