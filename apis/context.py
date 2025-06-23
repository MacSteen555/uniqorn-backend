from fastapi import APIRouter
from schemas.chat import ChatMessage
from schemas.context import ProjectContext
from agents.context import ContextAgent
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/context")
async def create_context(chat_history: list[ChatMessage]) -> ProjectContext:
    agent = ContextAgent()

    context = await agent.generate_project_context(chat_history=chat_history)

    return context