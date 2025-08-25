import asyncio
import functools
import os
from dotenv import load_dotenv

from firecrawl import FirecrawlApp
from schemas.tools import FirecrawlMarkdown, FirecrawlURL


load_dotenv()
app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))

# Make synchronous search work in async context
async def search_urls(query: str) -> list[FirecrawlURL]:
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(
        None,
        functools.partial(
            app.search,
            query=query,
            limit=8
        )
    )
    
    output = []
    for result in resp.data:
        output.append(FirecrawlURL(
            url=result["url"], 
            title=result["title"], 
            description=result["description"]
        ))

    return output

async def fetch_sites_markdown(
    urls: list[str],
) -> list[FirecrawlMarkdown]:
    tasks = [fetch_site_markdown(url) for url in urls]
    return await asyncio.gather(*tasks)

async def fetch_site_markdown(
    url: str,
) -> FirecrawlMarkdown:
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(
        None,
        functools.partial(
            app.scrape_url,
            url,
            formats=["markdown", "links"],
        )
    )
    return FirecrawlMarkdown(url=url, markdown=resp.markdown or "", links=resp.links or [])

async def main():
    print("Testing Firecrawl tools...")
    
    # Test search
    print("\nTesting search_urls:")
    search_results = await search_urls("artificial intelligence latest developments")
    print(f"Found {len(search_results)} search results")
    
    if search_results:
        print(f"First result: {search_results[0].title}")
        print(f"URL: {search_results[0].url}")
        
        # Test fetch single markdown
        print("\nTesting fetch_site_markdown:")
        markdown_result = await fetch_site_markdown(search_results[0].url)
        print(f"Fetched markdown from {markdown_result.url}")
        print(f"Markdown length: {len(markdown_result.markdown)} characters")
        print(f"Number of links: {len(markdown_result.links)}")
        
        # Test fetch multiple markdowns
        print("\nTesting fetch_sites_markdown:")
        urls = [result.url for result in search_results[:2]]
        markdown_results = await fetch_sites_markdown(urls)
        print(f"Fetched {len(markdown_results)} markdown documents")

if __name__ == "__main__":
    asyncio.run(main())


