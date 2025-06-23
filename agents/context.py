import json
import os
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from openai import OpenAI
from dotenv import load_dotenv

from schemas.chat import ChatMessage
from schemas.context import ProjectContext
from utils.prompt import load_prompt
from utils.llm import generate_response

load_dotenv()

client = OpenAI()

class ContextAgent:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "context.yaml"
        system_prompt = load_prompt(self.prompt_path, "system_prompt")
        
        mini_model = OpenAIModel(
            model_name="gpt-4.1-mini",
            provider=OpenAIProvider(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY")),
        )
        
        standard_model = OpenAIModel(
            model_name="gpt-4.1",
            provider=OpenAIProvider(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.getenv("OPENAI_API_KEY")),
        )

        self.mini_agent = Agent(
            model=mini_model,
            retries=2,
            system_prompt=system_prompt,
            instrument=True,
        )

        self.standard_agent = Agent(
            model=standard_model,
            retries=3,
            system_prompt=system_prompt,
            instrument=True,
        )

    async def generate_project_context(self, chat_history: list[ChatMessage]) -> ProjectContext:
        """Generate project context using OpenAI responses API with web search and reasoning."""
        
        # Prepare chat history
        chat_history_dicts = [msg.model_dump() for msg in chat_history]
        
        # Load the prompt from YAML (same as before)
        prompt = load_prompt(self.prompt_path, "project_context", chat_history=json.dumps(chat_history_dicts))
        
        try:
            # Call the responses API with web search and reasoning
            result = generate_response(
                user_prompt=prompt,
                system_prompt=None,  # Use the prompt from YAML as the main prompt
                model="gpt-4.1",
                temperature=0.7,
                max_tokens=4096,
                enable_web_search=True,
            )
            
            # Check if we got valid JSON
            if result["json"]:
                # Create ProjectContext from parsed JSON
                project_context = ProjectContext(**result["json"])
                return project_context
            else:
                # Fallback: try to extract structured data from text
                print(f"Warning: Could not parse JSON from response. Response text: {result['text'][:200]}...")
                
                response = await self.standard_agent.run(
                    user_prompt=prompt,
                    output_type=ProjectContext,
                )
                
                return response.output
                
        except Exception as e:
            print(f"Error calling responses API: {e}")
            
            # Fallback to original mini_agent approach
            response = await self.mini_agent.run(
                output_type=ProjectContext,
                user_prompt=prompt,
            )
            return response.output
