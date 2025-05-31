import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_responses_api():
    """Test the OpenAI responses API with a simple call."""
    
    # Initialize client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        print("Testing OpenAI responses API...")
        
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "What is 2+2? Please show your reasoning."
                        }
                    ]
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            reasoning={},  # Enable reasoning
            tools=[],  # No tools for this test
            temperature=0.7,
            max_output_tokens=1024,
            top_p=1,
            store=True
        )
        
        print("✅ API call successful!")
        print("\n--- Raw Response ---")
        print(response)
        print(f"\nResponse type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        return False


def test_responses_api_with_web_search():
    """Test the responses API with web search tool."""
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        print("\nTesting OpenAI responses API with web search...")
        
        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "What are the latest AI startup trends in 2024?"
                        }
                    ]
                }
            ],
            text={
                "format": {
                    "type": "text"
                }
            },
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {
                        "type": "approximate",
                        "country": "US",
                        "region": "California",
                        "city": "San Francisco"
                    },
                    "search_context_size": "medium"
                }
            ],
            temperature=0.7,
            max_output_tokens=2048,
            top_p=1,
            store=True
        )
        
        print("✅ Web search API call successful!")
        print("\n--- Raw Response ---")
        print(response)
        print(f"\nResponse type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Web search API call failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        exit(1)
    
    print("🧪 Testing OpenAI Responses API\n")
    
    # Test basic responses API
    basic_test = test_responses_api()
    
    # Test with web search
    web_search_test = test_responses_api_with_web_search()
    
    print(f"\n📊 Results:")
    print(f"Basic API: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"Web Search: {'✅ PASS' if web_search_test else '❌ FAIL'}")
    
    if basic_test and web_search_test:
        print("\n🎉 All tests passed! The responses API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check your API access or model availability.") 