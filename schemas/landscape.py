from pydantic import BaseModel
from typing import Literal, Optional
from datetime import date

class DateValue(BaseModel):
    date: date
    market_value: float  # in millions USD

class GrowthChart(BaseModel):
    points: list[DateValue]
    cagr: float  # Compound Annual Growth Rate in percentage
    market_info: str
    currency: Literal['USD', 'EUR', 'GBP', 'CAD'] = 'USD'
    interval: Literal['monthly', 'quarterly', 'yearly'] = 'yearly'
    source: str  # URL or reference to the data source
    market_drivers: Optional[list[str]]
    market_barriers: Optional[list[str]]

class Action(BaseModel):
    start: str
    finish: str

class Feature(BaseModel):
    name: str
    problem: str
    solution: str
    how_its_executed: str

class UserStory(BaseModel):
    outcome: str
    user_actions: list[Action]
    features: list[Feature]

class Product(BaseModel):
    user_stories: list[UserStory]
    differentiators: list[str]

class NewsArticle(BaseModel):
    title: str
    url: str
    date: date

class Review(BaseModel):
    title: str
    review: str
    rating: float
    source: str
    date: date
    key_takeaways: list[str]

class Source(BaseModel):
    title: str
    description: str
    url: str

class Card(BaseModel):
    company: str
    competitive_product: Product
    industry: str
    description: str
    news: list[NewsArticle]
    revenue: Optional[float]  # in millions USD
    valuation: Optional[float]  # in millions USD
    funding_raised: Optional[float]  # in millions USD
    profitability: Optional[Literal['profitable', 'break-even', 'burning']]
    key_partners: Optional[list[str]]
    pricing_models: Optional[list[str]]
    public_company: bool
    notable_customers: Optional[list[str]]
    acquisitions: Optional[list[str]]
    employees: Optional[int]
    users: Optional[int]
    target_audiences: list[str]
    market_dominance: Literal['leader', 'challenger', 'niche', 'emerging']
    founded: date
    how_to_differentiate: list[str]
    reviews: list[Review]
    headquarters: Optional[str]
    regions_operated: Optional[list[str]]
    sources: Optional[list[Source]]

class Opportunity(BaseModel):
    title: str
    description: str
    impact: Optional[str]  # e.g., 'High', 'Medium', 'Low'
    timeframe: Optional[str]  # e.g., 'Short-term', 'Long-term'

class Challenge(BaseModel):
    title: str
    description: str
    severity: Optional[str]  # e.g., 'Critical', 'Moderate', 'Low'
    mitigation_strategy: Optional[str]

class InvestmentTrend(BaseModel):
    year: int
    top_investors: Optional[list[str]]
    total_investment: float  # in millions USD
    notable_investments: Optional[list[str]]
    investor_types: Optional[list[str]]  # e.g., ['Venture Capital', 'Private Equity']
    notes: Optional[str]

class ExecutiveSummary(BaseModel):
    overview: str
    key_findings: list[str]
    risks: Optional[list[str]]
    market_outlook: Optional[str]
    strategic_recommendations: Optional[list[str]]

class IntermediateMarketReport(BaseModel):
    growth_chart: GrowthChart
    opportunities: list[Opportunity]
    challenges: list[Challenge]
    investment_trends: list[InvestmentTrend]
    executive_summary: ExecutiveSummary

class MarketResearchReport(BaseModel):
    growth_chart: GrowthChart
    opportunities: list[Opportunity]
    challenges: list[Challenge]
    investment_trends: list[InvestmentTrend]
    executive_summary: ExecutiveSummary
    parallel_companies: Optional[list[Card]]
    competitive_companies: Optional[list[Card]]