import asyncio
import os
import datetime as _dt
import requests
from schemas.tools import NewsArticle, NewsSearchInput

from dotenv import load_dotenv
from agents import function_tool

load_dotenv()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWS_ENDPOINT = "https://newsapi.org/v2/everything?"


@function_tool
async def news_search(input: NewsSearchInput) -> list[NewsArticle]:
    """Search global news for the last `days_back` days."""
    print("using newsapi")
    from_date = (_dt.datetime.now(_dt.UTC) - _dt.timedelta(days=input.days_back)).strftime("%Y-%m-%d")
    params = {
        "q": input.query,
        "from": from_date,
        "language": input.language,
        "pageSize": input.page_size,
        "sortBy": "relevancy",
        "apiKey": NEWSAPI_KEY,
    }
    r = requests.get(NEWS_ENDPOINT, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return [
        NewsArticle(
            source=a["source"]["name"],
            author=a.get("author"),
            title=a["title"],
            url=a["url"],
            published_at=a["publishedAt"],
            description=a.get("description"),
        )
        for a in data.get("articles", [])
    ]

async def main():
    print("Testing News API tool...")
    
    # Test with a current tech topic
    query = "machine learning startups"
    print(f"Searching for news about: {query}")
    
    results = await news_search(query)
    print(f"Found {len(results)} news articles")
    
    if results:
        print("\nTop 3 articles:")
        for i, article in enumerate(results[:3], 1):
            print(f"\n{i}. {article.title}")
            print(f"   Source: {article.source}")
            print(f"   Published: {article.published_at}")
            print(f"   URL: {article.url}")
            print(f"   Description: {article.description[:100]}..." if article.description else "   No description")

if __name__ == "__main__":
    asyncio.run(main())