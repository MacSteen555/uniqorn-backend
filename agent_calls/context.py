import json
import os
from pathlib import Path
from agents import Agent, Runner
from agents.model_settings import ModelSettings
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
        
        # Configure model settings
        self.model_settings = ModelSettings(
            temperature=0.7,
            max_tokens=4096,
            tool_choice="none",
        )

        self.mini_agent = Agent(
            name="Context Mini Agent",
            model="gpt-4.1-mini",
            instructions=system_prompt,
            model_settings=self.model_settings,
        )

        self.standard_agent = Agent(
            name="Context Standard Agent",
            model="gpt-4.1",
            instructions=system_prompt,
            model_settings=self.model_settings,
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
                
                result = await Runner.run(
                    self.standard_agent,
                    input=prompt,
                )
                
                # Parse the response to create ProjectContext
                try:
                    response_data = json.loads(result.final_output)
                    return ProjectContext(**response_data)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Error parsing context response: {e}")
                    # Return a default context
                    return ProjectContext(
                        name="Default Project",
                        description="Default project description",
                        target_audience="General users",
                        business_goals=["Default goal"],
                        success_metrics=["Default metric"],
                        budget="Not specified",
                        timeline="Not specified",
                        team_size="1-2 people",
                        technical_level="Beginner",
                        project_type="MVP"
                    )
                
        except Exception as e:
            print(f"Error calling responses API: {e}")
            
            # Fallback to original mini_agent approach
            result = await Runner.run(
                self.mini_agent,
                input=prompt,
            )
            
            try:
                response_data = json.loads(result.final_output)
                return ProjectContext(**response_data)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Error parsing context response: {e}")
                # Return a default context
                return ProjectContext(
                    name="Default Project",
                    description="Default project description",
                    target_audience="General users",
                    business_goals=["Default goal"],
                    success_metrics=["Default metric"],
                    budget="Not specified",
                    timeline="Not specified",
                    team_size="1-2 people",
                    technical_level="Beginner",
                    project_type="MVP"
                )
