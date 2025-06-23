from typing import List, Literal, Optional
from pydantic import BaseModel

class Company(BaseModel):
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
    parallel_companies: List[Company] = []
    competitive_companies: List[Company] = []
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