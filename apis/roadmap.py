import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.chat import ChatMessage
from schemas.context import ProjectContext
from schemas.roadmap import Roadmap
from agents.roadmap import RoadmapAgent
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/roadmap")
async def create_roadmap(context: ProjectContext) -> Roadmap:
    agent = RoadmapAgent()

    epics = await agent.generate_epics(project_context=context)
    
    # Generate features for each epic ASYNCHRONOUSLY
    async def generate_features_safe(epic):
        try:
            return await agent.generate_features(epic=epic, project_context=context)
        except Exception as e:
            logger.error(f"Failed to generate features for epic {epic.id}: {e}")
            return []
    
    features_lists = await asyncio.gather(*[generate_features_safe(epic) for epic in epics])
    features = [feature for feature_list in features_lists if feature_list is not None for feature in feature_list]
    
    # Generate tasks for each feature ASYNCHRONOUSLY
    async def generate_tasks_safe(feature):
        try:
            return await agent.generate_tasks(feature=feature)
        except Exception as e:
            logger.error(f"Failed to generate tasks for feature {feature.id}: {e}")
            return []
    tasks_lists = await asyncio.gather(*[generate_tasks_safe(feature) for feature in features])
    # Filter out None values and flatten
    tasks = [task for task_list in tasks_lists if task_list is not None for task in task_list]

    # Combine all items
    all_items = epics + features + tasks
    # Build parent-child relationships
    def populate_children_ids(items):
        children_map = {}
        for item in items:
            if item.parent_id:
                if item.parent_id not in children_map:
                    children_map[item.parent_id] = []
                children_map[item.parent_id].append(item.id)
        
        for item in items:
            item.children_ids = children_map.get(item.id, [])
        
        return items
    
    all_items = populate_children_ids(all_items)

    return Roadmap(
        context=context,
        items=all_items,
        last_exported_to_jira=None,
        last_exported_to_notion=None,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        version="1.0"
    )

