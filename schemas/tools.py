from pydantic import BaseModel, Field, validator
import datetime as _dt

class FirecrawlMarkdown(BaseModel):
    url: str
    markdown: str
    links: list[str]

class FirecrawlURL(BaseModel):
    url: str
    title: str
    description: str


class PHPost(BaseModel):
    id: str
    name: str
    tagline: str | None
    votes: int = Field(..., alias="votesCount")
    featured_at: _dt.datetime | None
    url: str

    # Product Hunt API returns timestamps as ISO‑8601 strings.
    @validator("featured_at", pre=True)
    def _parse_ts(cls, v):
        return _dt.datetime.fromisoformat(v.rstrip("Z")) if v else None
    

class TrendResult(BaseModel):
    keyword: str
    timeline: list[dict]  # [{"date": "2024-05-12", "value": 57}, ...]


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

class NewsArticle(BaseModel):
    source: str
    author: str | None
    title: str
    url: str
    published_at: str
    description: str | None