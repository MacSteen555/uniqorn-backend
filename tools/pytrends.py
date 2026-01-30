from pytrends.request import TrendReq
from schemas.tools import TrendResult  # type: ignore – install pytrends
from datetime import datetime

from agents import function_tool
import logging

logger = logging.getLogger(__name__)

@function_tool
async def trends_get(keyword: str, timeframe: str = "today 12-m") -> TrendResult:
    """Return interest‑over‑time values for a single keyword."""
    logger.info(f"using pytrends for keyword: {keyword}")
    pytrends = TrendReq(hl="en-US", tz=0)
    pytrends.build_payload([keyword], timeframe=timeframe)
    df = pytrends.interest_over_time()
    
    # Convert datetime objects to ISO format strings for JSON serialization
    timeline = []
    for _, row in df.reset_index().iterrows():
        date_value = row['date']
        if isinstance(date_value, datetime):
            date_str = date_value.isoformat()
        else:
            date_str = str(date_value)
        
        timeline.append({
            "date": date_str,
            "value": int(row[keyword])
        })
    
    return TrendResult(keyword=keyword, timeline=timeline)


async def main():
    print("Testing Google Trends tool...")
    
    # Test with a trending tech term
    keyword = "generative AI"
    print(f"Fetching trend data for: {keyword}")
    
    result = await trends_get(keyword)
    print(f"Retrieved trend data for: {result.keyword}")
    print(f"Timeline entries: {len(result.timeline)}")
    
    if result.timeline:
        print("\nSample trend points:")
        # Show first, middle and last points
        points_to_show = [0, len(result.timeline)//2, -1]
        for i in points_to_show:
            point = result.timeline[i]
            print(f"Date: {point['date']}, Value: {point['value']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
