from pydantic import BaseModel, Field, validator
import datetime as _dt
from typing import List

class FirecrawlMarkdown(BaseModel):
    url: str
    markdown: str
    links: list[str]

class FirecrawlURL(BaseModel):
    url: str
    title: str
    description: str

class PHInput(BaseModel):
    keyword: str = Field(..., description="Search keyword or product name")
    first: int = Field(30, description="Number of results to return (max 50)")
    order_by: str = Field("VOTES", description="Sort order: VOTES, NEWEST, TRENDING")
    category: str = Field("", description="Category filter (e.g., 'Productivity', 'Developer Tools')")
    time_period: str = Field("", description="Time period: 'TODAY', 'THIS_WEEK', 'THIS_MONTH', 'THIS_YEAR'")
    search_type: str = Field("KEYWORD", description="Search type: KEYWORD, CATEGORY, TRENDING, FEATURED")

class PHPost(BaseModel):
    id: str
    name: str
    tagline: str | None
    description: str | None = Field(None, description="Product description")
    votesCount: int = Field(..., alias="votesCount")
    featured_at: _dt.datetime | None
    url: str
    website: str | None = Field(None, description="Product website URL")
    pricing_type: str | None = Field(None, description="Free, Paid, Freemium, etc.")
    category: str | None = Field(None, description="Product category")
    makers: List[str] = Field(default_factory=list, description="List of makers/creators")
    comments_count: int = Field(0, description="Number of comments")
    created_at: _dt.datetime | None = Field(None, description="When the product was created")
    updated_at: _dt.datetime | None = Field(None, description="When the product was last updated")
    topics: List[str] = Field(default_factory=list, description="Product topics/tags")
    screenshot_url: str | None = Field(None, description="Product screenshot URL")

    # Product Hunt API returns timestamps as ISO‑8601 strings.
    @validator("featured_at", "created_at", "updated_at", pre=True)
    def _parse_ts(cls, v):
        return _dt.datetime.fromisoformat(v.rstrip("Z")) if v else None
    

class TrendResult(BaseModel):
    keyword: str
    timeline: list[dict]  # [{"date": "2024-05-12", "value": 57}, ...]
    
    def model_dump_json(self, **kwargs) -> str:
        """Custom JSON serialization to handle datetime objects in timeline data."""
        import json
        from datetime import datetime
        
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        data = self.model_dump()
        return json.dumps(data, default=json_serializer, ensure_ascii=False, **kwargs)


class RedditPost(BaseModel):
    id: str
    title: str
    score: int
    url: str
    subreddit: str
    created_utc: float

    @property
    def created_iso(self) -> str:
        return _dt.datetime.utcfromtimestamp(self.created_utc).isoformat() + "Z"

# Add these models to your schemas/tools.py file
class RedditComment(BaseModel):
    author: str
    body: str
    score: int
    created_utc: float
    
    def format_date(self) -> str:
        """Format the UTC timestamp as a readable date"""
        return _dt.datetime.fromtimestamp(self.created_utc).strftime("%Y-%m-%d %H:%M:%S")

class RedditPostDetail(BaseModel):
    title: str
    author: str
    selftext: str
    score: int
    upvote_ratio: float
    url: str
    created_utc: float
    num_comments: int
    subreddit: str
    is_original_content: bool
    top_comments: list[RedditComment]
    
    def format_date(self) -> str:
        """Format the UTC timestamp as a readable date"""
        return _dt.datetime.fromtimestamp(self.created_utc).strftime("%Y-%m-%d %H:%M:%S")

class NewsSearchInput(BaseModel):
    query: str
    days_back: int = 30
    language: str = "en"
    page_size: int = 20

class NewsArticle(BaseModel):
    source: str
    author: str | None
    title: str
    url: str
    published_at: str
    description: str | None

class Tool(BaseModel):
    name: str
    description: str
    url: str
    cost: str
    category: str


class ToolResponse(BaseModel):
    tools: List[Tool]
    reasoning: str