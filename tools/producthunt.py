import os
import requests
import time
from typing import List, Optional, Dict, Any

from schemas.tools import PHInput, PHPost
from dotenv import load_dotenv
from agents import FunctionTool, function_tool

load_dotenv()

import logging

# Configure logger
logger = logging.getLogger(__name__)

PH_ENDPOINT = "https://api.producthunt.com/v2/api/graphql"
PH_TOKEN = os.getenv("PRODUCTHUNT_DEV_TOKEN")

# Predefined categories for easy access
PRODUCT_HUNT_CATEGORIES = [
    "Developer Tools", "Productivity", "Design", "Marketing", "Analytics",
    "Communication", "Finance", "Education", "Health", "Entertainment",
    "Social Media", "E-commerce", "Mobile", "Web App", "API", "SaaS",
    "AI/ML", "Blockchain", "Gaming", "Music", "Video", "Photography"
]

# Search type descriptions for AI agents
SEARCH_TYPE_DESCRIPTIONS = {
    "KEYWORD": "Search for products by name, description, or topics",
    "CATEGORY": "Browse products in a specific category",
    "TRENDING": "Find currently trending products",
    "FEATURED": "Get products featured by Product Hunt",
    "POPULAR": "Get most voted products (default)"
}

def _ph_graphql(query: str, variables: dict) -> dict:
    """Execute a GraphQL query against the Product Hunt API with enhanced error handling."""
    if not PH_TOKEN:
        logger.warning("PRODUCTHUNT_DEV_TOKEN not found. Using limited functionality.")
        return {"data": {"posts": {"edges": []}}}
    
    headers = {
        "Authorization": f"Bearer {PH_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.post(
            PH_ENDPOINT, 
            json={"query": query, "variables": variables}, 
            headers=headers, 
            timeout=30
        )
        
        if resp.status_code != 200:
            logger.error(f"Product Hunt API error: {resp.status_code}")
            if resp.status_code == 401:
                logger.error("   Authentication failed. Check your API token.")
            elif resp.status_code == 429:
                logger.error("   Rate limit exceeded. Try again later.")
            return {"data": {"posts": {"edges": []}}}
        
        return resp.json()
    except requests.exceptions.Timeout:
        logger.error("Request timed out. Product Hunt API is slow to respond.")
        return {"data": {"posts": {"edges": []}}}
    except requests.exceptions.ConnectionError:
        logger.error("Connection error. Check your internet connection.")
        return {"data": {"posts": {"edges": []}}}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"data": {"posts": {"edges": []}}}

def _simplify_query_for_ai() -> str:
    """Simplified GraphQL query optimized for AI agent consumption."""
    return """
    query SearchPosts($first: Int!, $order: PostsOrder!, $query: String, $category: String) {
      posts(first: $first, order: $order, query: $query, category: $category) {
        edges {
          node {
            id
            name
            tagline
            description
            votesCount
            featuredAt
            url
            website
            pricingType
            category { name }
            makers { edges { node { name } } }
            commentsCount
            createdAt
            topics { edges { node { name } } }
            media { edges { node { type url } } }
          }
        }
      }
    }
    """

def _build_search_variables(input: PHInput) -> Dict[str, Any]:
    """Build search variables with intelligent defaults for AI agents."""
    
    # Set intelligent defaults
    variables = {
        "first": min(input.first, 50),  # Respect API limits
        "order": input.order_by or "VOTES",
        "query": None,
        "category": None
    }
    
    # Handle different search types
    if input.search_type == "KEYWORD" and input.keyword:
        variables["query"] = input.keyword
    elif input.search_type == "CATEGORY" and input.category:
        variables["category"] = input.category
    elif input.search_type == "TRENDING":
        variables["order"] = "TRENDING"
    elif input.search_type == "FEATURED":
        variables["order"] = "VOTES"  # Featured posts are typically high-vote
    elif input.search_type == "POPULAR":
        variables["order"] = "VOTES"
    
    return variables

def _extract_makers(makers_edges: List[dict]) -> List[str]:
    """Extract maker names from the makers edges."""
    if not makers_edges:
        return []
    return [edge["node"]["name"] for edge in makers_edges if edge["node"]["name"]]

def _extract_topics(topics_edges: List[dict]) -> List[str]:
    """Extract topic names from the topics edges."""
    if not topics_edges:
        return []
    return [edge["node"]["name"] for edge in topics_edges if edge["node"]["name"]]

def _extract_screenshot_url(media_edges: List[dict]) -> Optional[str]:
    """Extract screenshot URL from media edges."""
    if not media_edges:
        return None
    for edge in media_edges:
        if edge["node"]["type"] == "image":
            return edge["node"]["url"]
    return None

def _create_ai_friendly_post(node: dict) -> PHPost:
    """Create a PHPost object optimized for AI agent consumption."""
    
    # Extract nested data
    makers = _extract_makers(node.get("makers", {}).get("edges", []))
    topics = _extract_topics(node.get("topics", {}).get("edges", []))
    screenshot_url = _extract_screenshot_url(node.get("media", {}).get("edges", []))
    category_name = node.get("category", {}).get("name") if node.get("category") else None
    
    return PHPost(
        id=node["id"],
        name=node["name"],
        tagline=node.get("tagline"),
        description=node.get("description"),
        votesCount=node.get("votesCount", 0),
        featured_at=node.get("featuredAt"),
        url=node["url"],
        website=node.get("website"),
        pricing_type=node.get("pricingType"),
        category=category_name,
        makers=makers,
        comments_count=node.get("commentsCount", 0),
        created_at=node.get("createdAt"),
        updated_at=node.get("updatedAt"),
        topics=topics,
        screenshot_url=screenshot_url
    )

def _smart_keyword_search(posts: List[PHPost], keyword: str) -> List[PHPost]:
    """Perform intelligent keyword filtering with multiple matching strategies."""
    if not keyword:
        return posts
    
    keywords = keyword.lower().split()
    matched_posts = []
    
    for post in posts:
        # Check multiple fields for keyword matches
        searchable_text = [
            post.name.lower(),
            post.tagline.lower() if post.tagline else "",
            post.description.lower() if post.description else "",
            " ".join(post.topics).lower(),
            " ".join(post.makers).lower(),
            post.category.lower() if post.category else ""
        ]
        
        # Check if any keyword matches any searchable field
        for kw in keywords:
            if any(kw in text for text in searchable_text):
                matched_posts.append(post)
                break
    
    return matched_posts

@function_tool
async def producthunt_search(input: PHInput) -> List[PHPost]:
    """
    🔍 Search Product Hunt for products - Enhanced for Better Usability
    
    This tool provides comprehensive product research capabilities with improved search logic:
    
    📊 **Search Types:**
    - KEYWORD: Smart search by product name, description, topics, makers, or category
    - CATEGORY: Browse products in specific categories
    - TRENDING: Find currently trending products
    - FEATURED: Get Product Hunt featured products
    - POPULAR: Get most voted products (default)
    
    🎯 **Enhanced Features:**
    - Smart keyword matching across multiple fields
    - Intelligent fallbacks when searches fail
    - Better error handling and user feedback
    - Automatic category suggestions
    
    📈 **Returns rich data including:**
    - Product details, pricing, and engagement metrics
    - Maker information and team details
    - Categories, topics, and market positioning
    - Temporal data for trend analysis
    
    Example usage:
    - Find AI tools: keyword="AI assistant", search_type="KEYWORD"
    - Trending products: search_type="TRENDING"
    - Developer tools: category="Developer Tools", search_type="CATEGORY"
    """
    logger.info("using producthunt")
    # Validate and provide helpful feedback
    if not input.keyword and input.search_type == "KEYWORD":
        logger.info("Tip: For keyword search, provide a keyword. Trying popular products instead.")
        input.search_type = "POPULAR"
    
    if input.category and input.category not in PRODUCT_HUNT_CATEGORIES:
        logger.info(f"Tip: '{input.category}' not in known categories. Available: {', '.join(PRODUCT_HUNT_CATEGORIES[:5])}...")
        # Try to find a similar category
        similar_categories = [cat for cat in PRODUCT_HUNT_CATEGORIES if input.category.lower() in cat.lower()]
        if similar_categories:
            logger.info(f"   Similar categories found: {', '.join(similar_categories)}")
    
    # Build optimized query and variables
    gql = _simplify_query_for_ai()
    variables = _build_search_variables(input)
    
    try:
        # Fetch data
        data = _ph_graphql(gql, variables)
        
        # Extract and process results
        edges = data.get("data", {}).get("posts", {}).get("edges", [])
        
        if not edges:
            logger.info(f"No products found for: {input.search_type}")
            if input.keyword:
                logger.info(f"   Keyword: '{input.keyword}'")
            if input.category:
                logger.info(f"   Category: '{input.category}'")
            
            # Try fallback search if keyword search failed
            if input.search_type == "KEYWORD" and input.keyword:
                logger.info("Trying broader search...")
                # Try without the keyword to get some results
                fallback_variables = variables.copy()
                fallback_variables["query"] = None
                fallback_variables["order"] = "VOTES"
                fallback_data = _ph_graphql(gql, fallback_variables)
                fallback_edges = fallback_data.get("data", {}).get("posts", {}).get("edges", [])
                if fallback_edges:
                    logger.info("Found some products with broader search")
                    edges = fallback_edges
            
            if not edges:
                return []
        
        # Convert to AI-friendly post objects
        posts = [_create_ai_friendly_post(edge["node"]) for edge in edges]
        
        # Apply intelligent filtering
        if input.search_type == "FEATURED":
            posts = [post for post in posts if post.featured_at]
        
        # Apply smart keyword filtering for keyword searches
        if input.search_type == "KEYWORD" and input.keyword:
            posts = _smart_keyword_search(posts, input.keyword)
        
        # Limit results and provide feedback
        final_posts = posts[:input.first]
        
        logger.info(f"Found {len(final_posts)} products")
        if final_posts:
            top_post = final_posts[0]
            logger.info(f"   Top result: {top_post.name} ({top_post.votesCount} votes)")
            if top_post.category:
                logger.info(f"   Category: {top_post.category}")
            if top_post.pricing_type:
                logger.info(f"   Pricing: {top_post.pricing_type}")
        
        return final_posts
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

@function_tool
async def get_producthunt_categories() -> List[str]:
    """Get available Product Hunt categories for AI agent reference."""
    return PRODUCT_HUNT_CATEGORIES

@function_tool
async def get_producthunt_search_type_help() -> Dict[str, str]:
    """Get descriptions of available search types for AI agents."""
    return SEARCH_TYPE_DESCRIPTIONS

@function_tool
async def get_producthunt_trending() -> List[PHPost]:
    """Get currently trending products on Product Hunt."""
    input_data = PHInput(
        keyword="",
        search_type="TRENDING",
        first=10,
        order_by="TRENDING",
        category="",
        time_period=""
    )
    return await producthunt_search(input_data)

@function_tool
async def get_producthunt_featured() -> List[PHPost]:
    """Get featured products on Product Hunt."""
    input_data = PHInput(
        keyword="",
        search_type="FEATURED",
        first=10,
        order_by="VOTES",
        category="",
        time_period=""
    )
    return await producthunt_search(input_data)

def main():
    """Test the enhanced Product Hunt tool."""
    print("🚀 Enhanced Product Hunt Tool - AI Agent Optimized\n")
    
    # Test with different search types
    test_cases = [
        PHInput(keyword="AI assistant", search_type="KEYWORD", first=3, order_by="VOTES", category="", time_period=""),
        PHInput(keyword="", search_type="TRENDING", first=3, order_by="TRENDING", category="", time_period=""),
        PHInput(keyword="", search_type="FEATURED", first=3, order_by="VOTES", category="", time_period=""),
        PHInput(keyword="", category="Developer Tools", search_type="CATEGORY", first=3, order_by="VOTES", time_period="")
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_input.search_type} ---")
        if test_input.keyword:
            print(f"Keyword: {test_input.keyword}")
        if test_input.category:
            print(f"Category: {test_input.category}")
        
        print("(This would call the async function in a real scenario)")
        print(f"Would search for {test_input.first} products")

if __name__ == "__main__":
    main()
