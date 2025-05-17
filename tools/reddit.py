import os
import praw
from schemas.tools import RedditPost, RedditPostDetail, RedditComment
from langchain.tools import StructuredTool
from dotenv import load_dotenv

load_dotenv()

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "startup_landscape_app/0.1")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
)

def reddit_search(query: str, limit: int = 10, subreddit: str | None = None) -> list[RedditPost]:
    """Search Reddit with the given query. Uses subreddit='all' if none specified."""
    sr = reddit.subreddit(subreddit or "all")
    results = sr.search(query, sort="relevance", limit=limit, syntax="lucene")
    return [
        RedditPost(
            id=p.id,
            title=p.title,
            score=p.score,
            url=p.url,
            subreddit=str(p.subreddit),
            created_utc=p.created_utc,
        )
        for p in results
    ]

def reddit_get_post_details(post_id: str) -> RedditPostDetail:
    """Get detailed information about a specific Reddit post including comments."""
    try:
        # Get the submission by ID
        submission = reddit.submission(id=post_id)
        
        # Load comments (limit to top 10)
        submission.comments.replace_more(limit=0)  # Skip "load more comments" links
        top_comments = submission.comments.list()[:10]
        
        # Format comments
        formatted_comments = [
            RedditComment(
                author=str(comment.author) if comment.author else "[deleted]",
                body=comment.body,
                score=comment.score,
                created_utc=comment.created_utc
            )
            for comment in top_comments
        ]
        
        # Create detailed post info
        return RedditPostDetail(
            title=submission.title,
            author=str(submission.author) if submission.author else "[deleted]",
            selftext=submission.selftext,
            score=submission.score,
            upvote_ratio=submission.upvote_ratio,
            url=submission.url,
            created_utc=submission.created_utc,
            num_comments=submission.num_comments,
            subreddit=str(submission.subreddit),
            is_original_content=submission.is_original_content,
            top_comments=formatted_comments
        )
    
    except Exception as e:
        raise ValueError(f"Error getting post details: {e}")

reddit_tool = StructuredTool.from_function(
    name="reddit_search",
    description="Search Reddit posts (subreddit optional) and return a list sorted by relevance.",
    func=reddit_search,
)

reddit_post_tool = StructuredTool.from_function(
    name="reddit_get_post",
    description="Get detailed information about a specific Reddit post including top comments. Requires post ID.",
    func=reddit_get_post_details,
)

def main():
    print("Testing Reddit tools...")
    
    # Test with a general query
    query = "startup advice"
    print(f"Searching Reddit for: {query}")
    
    results = reddit_search(query)
    print(f"Found {len(results)} posts")
    
    if results:
        print("\nTop 3 posts:")
        for i, post in enumerate(results[:3], 1):
            print(f"\n{i}. {post.title}")
            print(f"   Post ID: {post.id}")
            print(f"   Subreddit: r/{post.subreddit}")
            print(f"   Score: {post.score}")
            print(f"   URL: {post.url}")
            
            # Get post details for the first result
            if i == 1:
                try:
                    details = reddit_get_post_details(post.id)
                    print(f"\n   Post details:")
                    print(f"   Author: {details.author}")
                    print(f"   Created: {details.format_date()}")
                    print(f"   Upvote ratio: {details.upvote_ratio}")
                    print(f"   Number of comments: {details.num_comments}")
                    
                    if details.top_comments:
                        print(f"\n   Top comment:")
                        comment = details.top_comments[0]
                        print(f"   {comment.author}: {comment.body[:100]}..." if len(comment.body) > 100 else comment.body)
                except Exception as e:
                    print(f"   Error getting post details: {e}")

if __name__ == "__main__":
    main()