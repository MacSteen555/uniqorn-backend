import asyncio
import json
import os
from pathlib import Path
from typing import Literal
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from openai import OpenAI
from dotenv import load_dotenv

from schemas.landscape import Card, IntermediateMarketReport
from schemas.context import Company, ProjectContext
from utils.llm import generate_response
from utils.prompt import load_prompt

load_dotenv()

client = OpenAI()

class LandscapeAgent:
    def __init__(self):
        self.prompt_path = Path(__file__).parent / "prompts" / "landscape.yaml"
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
    
    
    async def generate_card(self, company: Company, type: Literal["competitive", "parallel"], project_context: ProjectContext) -> Card:
        
        prompt = load_prompt(self.prompt_path, "generate_company_card", company_name=company.name, company_info=company.model_dump_json(), type=type, project_context=project_context.model_dump_json())
        
        result = generate_response(
            user_prompt=prompt,
            system_prompt=None,
            model="gpt-4.1",
            temperature=0.7,
            max_tokens=12000,
        )

        if result["json"]:
            return Card(**result["json"])
        else:
            print(f"Warning: Could not parse JSON from response. Response text: {result['text'][:200]}...")

            response = await self.standard_agent.run(
                output_type=Card,
                user_prompt=prompt,
            )
            return response.output

        
    
    async def research_market(
        self, 
        project_context: ProjectContext
    ) -> IntermediateMarketReport:
        
        try:
            # Load the market research prompt
            prompt = load_prompt(
                self.prompt_path, 
                "market_research_report", 
                project_context=project_context.model_dump_json()
            )
            
            print(f"Loaded prompt successfully. Prompt length: {len(prompt)}")
        
            # Use OpenAI responses API with web search for comprehensive research
            result = generate_response(
                user_prompt=prompt,
                system_prompt=None,  # Use the prompt from YAML as the main prompt
                model="gpt-4.1",
                temperature=0.7,
                max_tokens=12000,  # Increased for comprehensive reports
                enable_web_search=True,
            )
            
            print(f"Generated response. Status: {result.get('status')}")
            print(f"Response text length: {len(result.get('text', ''))}")
            print(f"JSON parsed: {result.get('json') is not None}")
            
            # Check if we got valid JSON
            if result["json"]:
                # Create IntermediateMarketReport from parsed JSON
                market_report = IntermediateMarketReport(**result["json"])
                return market_report
            else:
                # Fallback: try to extract structured data from text
                print(f"Warning: Could not parse JSON from response. Response text: {result['text'][:200]}...")
                
                # Use the agent as fallback
                response = await self.standard_agent.run(
                    user_prompt=prompt,
                    output_type=IntermediateMarketReport,
                )
                
                return response.output
                
        except Exception as e:
            print(f"Error in research_market: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise e