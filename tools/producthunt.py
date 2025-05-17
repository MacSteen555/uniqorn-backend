import os
import requests
import time
from typing import List
from langchain.tools import StructuredTool
from schemas.tools import PHPost
from dotenv import load_dotenv

load_dotenv()

PH_ENDPOINT = "https://api.producthunt.com/v2/api/graphql"
PH_TOKEN = os.getenv("PRODUCTHUNT_DEV_TOKEN")

def _ph_graphql(query: str, variables: dict) -> dict:
    """Execute a GraphQL query against the Product Hunt API."""
    headers = {
        "Authorization": f"Bearer {PH_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        resp = requests.post(
            PH_ENDPOINT, 
            json={"query": query, "variables": variables}, 
            headers=headers, 
            timeout=30
        )
        
        if resp.status_code != 200:
            return {"data": {"posts": {"edges": []}}}
        
        return resp.json()
    except Exception:
        return {"data": {"posts": {"edges": []}}}

def producthunt_search(keyword: str, first: int = 30) -> List[PHPost]:
    """Search Product Hunt posts by keyword and return a list of posts sorted by votes."""
    # Simple query to get top posts
    gql = """
    query GetTopPosts($first: Int!) {
      posts(order: VOTES, first: $first) {
        edges {
          node {
            id
            name
            tagline
            votesCount
            featuredAt
            url
          }
        }
      }
    }
    """
    
    try:
        # Fetch data
        data = _ph_graphql(gql, {"first": first})
        
        # Extract edges or return empty list
        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        
        # Filter results by keyword
        keywords = keyword.lower().split()
        filtered_edges = [
            edge for edge in edges 
            if any(kw in edge["node"]["name"].lower() for kw in keywords) or 
               (edge["node"]["tagline"] and any(kw in edge["node"]["tagline"].lower() for kw in keywords))
        ]
        
        # Convert to PHPost objects
        return [
            PHPost(
                id=edge["node"]["id"],
                name=edge["node"]["name"],
                tagline=edge["node"]["tagline"],
                votesCount=edge["node"]["votesCount"],
                featured_at=edge["node"]["featuredAt"],
                url=edge["node"]["url"]
            )
            for edge in filtered_edges
        ]
    except Exception:
        return []

producthunt_tool = StructuredTool.from_function(
    name="producthunt_search",
    description="Search Product Hunt for products related to a keyword and return a list sorted by votes.",
    func=producthunt_search,
)

def main():
    """Test the Product Hunt tool."""
    print("Testing Product Hunt tool...")
    
    # Test with a tech category
    keyword = "AI assistant"
    print(f"Searching for products related to: {keyword}")
    
    results = producthunt_search(keyword)
    print(f"Found {len(results)} products")
    
    if results:
        print("\nTop 3 products:")
        for i, product in enumerate(results[:3], 1):
            print(f"\n{i}. {product.name}")
            print(f"   Tagline: {product.tagline}")
            print(f"   Votes: {product.votes}")
            print(f"   URL: {product.url}")

if __name__ == "__main__":
    main()
