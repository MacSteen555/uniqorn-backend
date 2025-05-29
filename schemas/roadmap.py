from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Status(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"

class ItemType(str, Enum):
    EPIC = "epic"
    FEATURE = "feature"
    TASK = "task"
    BUG = "bug"
    SPIKE = "spike"  # Research/investigation

class Complexity(str, Enum):
    XS = "xs"  # 1-2 hours
    S = "s"    # 1-2 days
    M = "m"    # 3-5 days
    L = "l"    # 1-2 weeks
    XL = "xl"  # 2+ weeks

class Tool(BaseModel):
    name: str
    description: str
    url: str
    cost: str
    category: str  # "development", "design", "project-management", etc.

class Approach(BaseModel):
    name: str
    description: str
    time_estimate: str
    complexity: Complexity
    tools: List[Tool]
    pros: List[str]
    cons: List[str]
    technical_requirements: List[str] = []
    recommended_for: str  # "Non-technical teams", "Technical teams", "All teams"

class AcceptanceCriteria(BaseModel):
    id: str
    description: str
    completed: bool = False

class RoadmapItem(BaseModel):
    id: str
    title: str
    description: str
    type: ItemType
    priority: Priority
    status: Status
    
    # PM-friendly fields
    business_value: str  # "High user engagement", "Revenue increase", etc.
    user_story: Optional[str] = None  # "As a user, I want to..."
    acceptance_criteria: List[AcceptanceCriteria] = []
    
    # Technical fields
    approaches: List[Approach]
    complexity: Complexity
    estimated_hours: Optional[int] = None
    story_points: Optional[int] = None  # For agile teams
    
    # Relationships
    dependencies: List[str] = []  # Item IDs that must be completed first
    blocks: List[str] = []  # Item IDs that this blocks
    parent_epic: Optional[str] = None  # For tasks under epics
    
    # Metadata for exports
    labels: List[str] = []  # Tags for filtering/organization
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    
    # External system IDs for sync
    jira_id: Optional[str] = None
    notion_id: Optional[str] = None
    github_issue_id: Optional[str] = None

class ProjectContext(BaseModel):
    name: str
    description: str
    target_audience: str
    business_goals: List[str]
    success_metrics: List[str]
    
    # Resource constraints
    budget: str
    timeline: str
    team_size: str  # "1-2 people", "3-5 people", etc.
    technical_level: str
    
    # Project metadata
    industry: Optional[str] = None
    project_type: str  # "MVP", "Feature Enhancement", "Complete Rebuild", etc.
    
class Sprint(BaseModel):
    id: str
    name: str
    start_date: datetime
    end_date: datetime
    goal: str
    items: List[str]  # RoadmapItem IDs
    
class Milestone(BaseModel):
    id: str
    name: str
    description: str
    target_date: datetime
    completion_criteria: List[str]
    associated_items: List[str]  # RoadmapItem IDs

class Roadmap(BaseModel):
    id: str
    context: ProjectContext
    items: List[RoadmapItem]
    sprints: List[Sprint] = []
    milestones: List[Milestone] = []
    
    # Export metadata
    last_exported_to_jira: Optional[datetime] = None
    last_exported_to_notion: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"

