import json
import os
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from openai import OpenAI
from dotenv import load_dotenv

from schemas.chat import ChatMessage
from schemas.roadmap import ProjectContext, RoadmapItem
from utils.prompt import load_prompt

load_dotenv()

client = OpenAI()

class RoadmapAgent:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "roadmap.yaml"
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
        chat_history_dicts = [msg.model_dump() for msg in chat_history]
        prompt = load_prompt(self.prompt_path, "project_context", chat_history=json.dumps(chat_history_dicts))
        
        response = await self.mini_agent.run(
            output_type=ProjectContext,
            user_prompt=prompt,
        )

        return response.data
    
    async def generate_epics(self, project_context: ProjectContext) -> list[RoadmapItem]:
        prompt = load_prompt(self.prompt_path, "generate_epics", project_context=project_context.model_dump_json())

        response = await self.mini_agent.run(
            output_type=list[list[RoadmapItem]],
            user_prompt=prompt,
        )
        
        output = []
        y_position = 0.0
        for group in response.data:
            x_position = 0.0
            for item in group:
                item.position.x = x_position
                item.position.y = y_position
                x_position += 235.0
                output.append(item)
            y_position += 300.0

        return output
    
    async def generate_features(self, epic: RoadmapItem, project_context: ProjectContext) -> list[RoadmapItem] | None:
        prompt = load_prompt(self.prompt_path, "generate_features", epic=epic.model_dump_json(), project_context=project_context.model_dump_json())

        response = await self.mini_agent.run(
            output_type=list[list[RoadmapItem]],
            user_prompt=prompt,
        )
        if response.data is None:
            return None

        output = []
        y_position = 0.0
        for group in response.data:
            x_position = 0.0
            for item in group:
                item.parent_id = epic.id
                item.position.x = x_position
                item.position.y = y_position
                x_position += 235.0
                output.append(item)
            y_position += 300.0

        return output

    async def generate_tasks(self, feature: RoadmapItem) -> list[RoadmapItem] | None:
        prompt = load_prompt(self.prompt_path, "generate_tasks", feature=feature.model_dump_json())

        response = await self.mini_agent.run(
            output_type=list[list[RoadmapItem]],
            user_prompt=prompt,
        )
        if response.data is None:
            return None

        output = []
        y_position = 0.0
        for group in response.data:
            x_position = 0.0
            for item in group:
                item.parent_id = feature.id
                item.position.x = x_position
                item.position.y = y_position
                x_position += 235.0
                output.append(item)
            y_position += 300.0

        return output
