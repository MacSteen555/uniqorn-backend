from typing import Optional, List, Union, Literal
import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from pydantic.json_schema import SkipJsonSchema


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

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Tool(BaseModel):
    name: str
    description: str
    url: str
    cost: str
    category: str  # "development", "design", "project-management", etc.

class Approach(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    pros: List[str]
    cons: List[str]
    effort_estimate: Optional[str] = None
    risk_level: Optional[RiskLevel] = None

class AcceptanceCriteria(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    completed: SkipJsonSchema[bool] = Field(default=False)

class Position(BaseModel):
    x: float
    y: float

class RoadmapItem(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    type: Literal["epic", "feature", "task"]
    priority: Priority
    status: Status

    parent_id: SkipJsonSchema[Optional[str]] = None
    children_ids: SkipJsonSchema[List[str]] = []
    
    # PM-friendly fields
    business_value: str  # "High user engagement", "Revenue increase", etc.
    user_story: Optional[str] = None  # "As a user, I want to..."
    acceptance_criteria: List[AcceptanceCriteria]
    
    # Technical fields
    approaches: List[Approach]
    complexity: Complexity
    estimated_hours: Optional[int] = None
    story_points: Optional[int] = None  # For agile teams
    
    # Relationships
    dependencies: List[str] = []  # Item IDs that must be completed first
    blocks: List[str] = []  # Item IDs that this blocks
    
    # Metadata for exports
    labels: List[str] = []  # Tags for filtering/organization
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created_at: SkipJsonSchema[str] = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: SkipJsonSchema[str] = Field(default_factory=lambda: datetime.now().isoformat())
    due_date: Optional[str] = None
    
    # External system IDs for sync
    jira_id: Optional[str] = None
    notion_id: Optional[str] = None
    github_issue_id: Optional[str] = None
    
    # Canvas-specific
    position: SkipJsonSchema[Position] = Field(default_factory=lambda: Position(x=0.0, y=0.0))


class ParallelCompany(BaseModel):
    name: str
    positioning: str
    strengths: List[str]
    weaknesses: List[str]

class CompetitiveCompany(BaseModel):
    name: str
    positioning: str
    strengths: List[str]
    weaknesses: List[str]

class KeyFeature(BaseModel):
    name: str
    description: str
    priority: Literal[1, 2, 3, 4, 5]

class Differentiator(BaseModel):
    name: str
    description: str
    priority: Literal[1, 2, 3, 4, 5]

class GoToMarket(BaseModel):
    channels: List[str]
    launch_plan: List[str]

class BusinessModel(BaseModel):
    value_proposition: str
    revenue_stream: str
    pricing_strategy: str

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
    
    # Startup-specific fields from OpenAI prompt
    user_pitch: Optional[str] = None
    parallel_companies: Optional[List[ParallelCompany]] = None
    competitive_companies: Optional[List[CompetitiveCompany]] = None
    key_features: Optional[List[KeyFeature]] = None
    standard_features: Optional[List[str]] = None
    differentiators: Optional[List[Differentiator]] = None
    development_ideas: Optional[List[str]] = None
    technical_requirements: Optional[List[str]] = None
    problems: Optional[List[str]] = None
    solutions: Optional[List[str]] = None
    need_for_solutions: Optional[List[str]] = None
    retention_strategies: Optional[List[str]] = None
    go_to_market: Optional[GoToMarket] = None
    business_model: Optional[BusinessModel] = None

class Sprint(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    start_date: str
    end_date: str
    goal: str
    items: List[str]  # RoadmapItem IDs
    
class Milestone(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    target_date: str
    completion_criteria: List[str]
    associated_items: List[str]  # RoadmapItem IDs

class Roadmap(BaseModel):
    id: SkipJsonSchema[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    context: ProjectContext
    items: List[RoadmapItem]
    
    # Export metadata
    last_exported_to_jira: Optional[str] = None
    last_exported_to_notion: Optional[str] = None
    
    created_at: SkipJsonSchema[str] = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: SkipJsonSchema[str] = Field(default_factory=lambda: datetime.now().isoformat())
    version: str

# Legacy support for current canvas
class InstructionVerb(str, Enum):
    UPSERT = "upsert"
    DELETE = "delete"
    UPDATE_PROPERTY = "update_property"

class Instruction(BaseModel):
    verb: InstructionVerb
    element: Optional[RoadmapItem] = None
    id: Optional[str] = None
    property: Optional[str] = None
    value: Optional[Union[str, int, bool, List, dict]] = None

class CanvasJSON(BaseModel):
    version: str
    instructions: List[Instruction]
    elements: Optional[List[RoadmapItem]] = None