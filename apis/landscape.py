import asyncio
from fastapi import APIRouter
from datetime import datetime
from agent_calls.landscape import LandscapeAgent
from schemas.chat import ChatMessage
from schemas.landscape import MarketResearchReport
from schemas.context import ProjectContext
from schemas.roadmap import Roadmap
from agent_calls.roadmap import RoadmapAgent
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/landscape")
async def create_landscape(context: ProjectContext) -> MarketResearchReport:
    agent = LandscapeAgent()

    competitive_tasks = [agent.generate_card(type="competitive", project_context=context, company=company) for company in context.competitive_companies]
    parallel_tasks = [agent.generate_card(type="parallel", project_context=context, company=company) for company in context.parallel_companies]
    
    # Run all tasks asynchronously
    competitive_cards, parallel_cards, market_report = await asyncio.gather(
        asyncio.gather(*competitive_tasks),
        asyncio.gather(*parallel_tasks),
        agent.research_market(context)
    )

    cleaned_parallel_cards = [card for card in parallel_cards if card is not None]
    cleaned_competitive_cards = [card for card in competitive_cards if card is not None]

    return MarketResearchReport(
        growth_chart=market_report.growth_chart,
        opportunities=market_report.opportunities,
        challenges=market_report.challenges,
        investment_trends=market_report.investment_trends,
        executive_summary=market_report.executive_summary,
        parallel_companies=cleaned_parallel_cards,
        competitive_companies=cleaned_competitive_cards,
    )

