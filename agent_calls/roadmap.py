import json
import os
from pathlib import Path
from agents import Agent, Runner
from agents.model_settings import ModelSettings
from openai import OpenAI
from dotenv import load_dotenv
from typing import List

from schemas.chat import ChatMessage
from schemas.context import ProjectContext
from schemas.roadmap import RoadmapItem
from utils.prompt import load_prompt
from utils.llm import generate_response

load_dotenv()

client = OpenAI()

class RoadmapAgent:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "roadmap.yaml"
        system_prompt = load_prompt(self.prompt_path, "system_prompt")
        
        # Configure model settings
        self.model_settings = ModelSettings(
            temperature=0.7,
            max_tokens=4000,
            tool_choice="none",
        )

        self.mini_agent = Agent(
            name="Roadmap Mini Agent",
            model="gpt-4.1-mini",
            instructions=system_prompt,
            model_settings=self.model_settings,
        )

        self.standard_agent = Agent(
            name="Roadmap Standard Agent",
            model="gpt-4.1",
            instructions=system_prompt,
            model_settings=self.model_settings,
        )
    
    async def generate_epics(self, project_context: ProjectContext) -> list[RoadmapItem]:
        prompt = load_prompt(self.prompt_path, "generate_epics", project_context=project_context.model_dump_json())

        result = await Runner.run(
            self.mini_agent,
            input=prompt,
        )
        
        # Parse the response to extract roadmap items
        # Note: You'll need to implement proper JSON parsing here
        # This is a simplified version - you may need to adjust based on your actual response format
        try:
            response_data = json.loads(result.final_output)
            output = []
            y_position = 0.0
            
            # Assuming response_data is a list of groups
            for group in response_data:
                x_position = 0.0
                for item_data in group:
                    # Create RoadmapItem from item_data
                    item = RoadmapItem(**item_data)
                    item.position.x = x_position
                    item.position.y = y_position
                    x_position += 235.0
                    output.append(item)
                y_position += 300.0

            return output
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing roadmap response: {e}")
            return []
    
    async def generate_features(self, epic: RoadmapItem, project_context: ProjectContext) -> list[RoadmapItem] | None:
        prompt = load_prompt(self.prompt_path, "generate_features", epic=epic.model_dump_json(), project_context=project_context.model_dump_json())

        result = await Runner.run(
            self.mini_agent,
            input=prompt,
        )
        
        try:
            response_data = json.loads(result.final_output)
            output = []
            y_position = 0.0
            
            for group in response_data:
                x_position = 0.0
                for item_data in group:
                    item = RoadmapItem(**item_data)
                    item.parent_id = epic.id
                    item.position.x = x_position
                    item.position.y = y_position
                    x_position += 235.0
                    output.append(item)
                y_position += 300.0

            return output
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing features response: {e}")
            return None

    async def generate_tasks(self, feature: RoadmapItem) -> list[RoadmapItem] | None:
        prompt = load_prompt(self.prompt_path, "generate_tasks", feature=feature.model_dump_json())

        result = await Runner.run(
            self.mini_agent,
            input=prompt,
        )
        
        try:
            response_data = json.loads(result.final_output)
            output = []
            y_position = 0.0
            
            for group in response_data:
                x_position = 0.0
                for item_data in group:
                    item = RoadmapItem(**item_data)
                    item.parent_id = feature.id
                    item.position.x = x_position
                    item.position.y = y_position
                    x_position += 235.0
                    output.append(item)
                y_position += 300.0

            return output
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error parsing tasks response: {e}")
            return None
