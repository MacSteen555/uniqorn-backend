import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Set up client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    # Your exact API call
    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "You are a startup research tool, conductinng research on the users startup."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "I would like to know more about the competitive intelligence industry. What are the key players and what are their strengths and weaknesses?"
                    }
                ]
            }
        ],
        text={
            "format": {
                "type": "text"
            }
        },
        reasoning={},
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
        temperature=1,
        max_output_tokens=,
        top_p=1,
        store=True
    )
    
    print("✅ API call successful!")
    print("\n--- Raw Response ---")
    print(response)
    print(f"\nResponse type: {type(response)}")
    print(f"Response attributes: {dir(response)}")
    
except Exception as e:
    print(f"❌ Error: {e}") 