import os
import datetime as _dt
import requests
from schemas.tools import NewsArticle
from langchain.tools import StructuredTool
from dotenv import load_dotenv

load_dotenv()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWS_ENDPOINT = "https://newsapi.org/v2/everything?"

def news_search(query: str, days_back: int = 30, language: str = "en", page_size: int = 20) -> list[NewsArticle]:
    """Search global news for the last `days_back` days."""
    from_date = (_dt.datetime.now(_dt.UTC) - _dt.timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "from": from_date,
        "language": language,
        "pageSize": page_size,
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

news_tool = StructuredTool.from_function(
    name="news_search",
    description="Search NewsAPI articles for a query (last 30 days).",
    func=news_search,
)

def main():
    print("Testing News API tool...")
    
    # Test with a current tech topic
    query = "machine learning startups"
    print(f"Searching for news about: {query}")
    
    results = news_search(query)
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
    main()