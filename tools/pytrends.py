from pytrends.request import TrendReq
from schemas.tools import TrendResult  # type: ignore – install pytrends

from langchain.tools import StructuredTool


def trends_get(keyword: str, timeframe: str = "today 12-m") -> TrendResult:
    """Return interest‑over‑time values for a single keyword."""
    pytrends = TrendReq(hl="en-US", tz=0)
    pytrends.build_payload([keyword], timeframe=timeframe)
    df = pytrends.interest_over_time()
    timeline = (
        df[[keyword]]
        .reset_index()
        .rename(columns={keyword: "value", "date": "date"})
        .to_dict("records")
    )
    return TrendResult(keyword=keyword, timeline=timeline)


trends_tool = StructuredTool.from_function(
    name="google_trends",
    description="Fetch Google search interest over the past 12 months for a keyword (uses pytrends).",
    func=trends_get,
)

def main():
    print("Testing Google Trends tool...")
    
    # Test with a trending tech term
    keyword = "generative AI"
    print(f"Fetching trend data for: {keyword}")
    
    result = trends_get(keyword)
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
    main()
