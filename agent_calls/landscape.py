import asyncio
import json
import os
from pathlib import Path
from typing import Literal
from openai import OpenAI
from agents import Agent, WebSearchTool, Runner
from agents.model_settings import ModelSettings
from dotenv import load_dotenv

from schemas.landscape import Card, IntermediateMarketReport
from schemas.context import Company, ProjectContext
from utils.llm import generate_response
from utils.prompt import load_prompt
from tools.newsapi import news_search
from tools.producthunt import get_producthunt_categories, get_producthunt_search_type_help, producthunt_search
from tools.pytrends import trends_get

load_dotenv()

client = OpenAI()

class LandscapeAgent:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "landscape.yaml"
        research_system_prompt = load_prompt(self.prompt_path, "research_system_prompt")

        # Configure model settings for the OpenAI Agents SDK
        self.model_settings = ModelSettings(
            temperature=0.7,
            max_tokens=12000,
            tool_choice="required",
            parallel_tool_calls=True,
        )

        # Create the agent using OpenAI Agents SDK
        self.research_agent = Agent(
            name="Market Research Agent",
            model="gpt-4.1",
            instructions=research_system_prompt,
            tools=[
                WebSearchTool(),
                news_search,
                producthunt_search,
                get_producthunt_categories,
                get_producthunt_search_type_help,
                trends_get,
            ],
            model_settings=self.model_settings,
        )

    async def generate_card(self, company: Company, type: Literal["competitive", "parallel"], project_context: ProjectContext) -> Card:
        
        prompt = load_prompt(self.prompt_path, "generate_company_card", company_name=company.name, company_info=company.model_dump_json(), type=type, project_context=project_context.model_dump_json())
        
        agent = self.research_agent
        agent.output_type = Card

        # Use the OpenAI Agents SDK with Runner
        response = await Runner.run(
            agent,
            input=prompt,
        )
        
        return response.final_output

    async def research_market(
        self, 
        project_context: ProjectContext
    ) -> IntermediateMarketReport:

        # Load the market research prompt
        prompt = load_prompt(
            self.prompt_path, 
            "market_research_report", 
            project_context=project_context.model_dump_json()
        )
        
        agent = self.research_agent
        agent.output_type = IntermediateMarketReport

        # Use the OpenAI Agents SDK with Runner
        response = await Runner.run(
            agent,
            input=prompt,
        )
        
        return response.final_output