import os
import json
import re
from typing import Dict, Any, Literal, Optional, List
from openai import OpenAI
from openai.types.shared_params.reasoning import Reasoning


def extract_response_text(response) -> str:
    """Extract text content from OpenAI responses API response."""
    for output in response.output:
        if output.type == "message":
            for content in output.content:
                if content.type == "output_text":
                    return content.text
    return ""


def extract_citations(response) -> List[Dict[str, str]]:
    """Extract citations from web search response."""
    citations = []
    for output in response.output:
        if output.type == "message":
            for content in output.content:
                if content.type == "output_text":
                    for annotation in content.annotations:
                        if annotation.type == "url_citation":
                            citations.append({
                                "url": annotation.url,
                                "title": annotation.title,
                                "start_index": annotation.start_index,
                                "end_index": annotation.end_index
                            })
    return citations


def parse_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from response text, handling markdown formatting."""
    try:
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to find JSON directly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        
        # Try to parse the entire response as JSON
        return json.loads(response_text)
        
    except json.JSONDecodeError:
        return None


def generate_response(
    user_prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gpt-4.1",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    enable_web_search: bool = False,
    reasoning: Optional[Literal["low", "medium", "high"]] = None
) -> Dict[str, Any]:

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Prepare input messages
    input_messages = []
    
    if system_prompt:
        input_messages.append({
            "role": "system",
            "content": [{"type": "input_text", "text": system_prompt}]
        })
    
    input_messages.append({
        "role": "user",
        "content": [{"type": "input_text", "text": user_prompt}]
    })
    
    # Prepare tools
    tools = []
    if enable_web_search:
        tools.append({
            "type": "web_search_preview",
            "user_location": {
                "type": "approximate",
                "country": "US",
                "region": "California",
                "city": "San Francisco"
            },
            "search_context_size": "medium"
        })
    
    reasoning_param = None
    if reasoning:
        reasoning_param = Reasoning(effort=reasoning)
    
    response = client.responses.create(
        model=model,
        input=input_messages,
        text={"format": {"type": "text"}},
        reasoning=reasoning_param,
        tools=tools,
        temperature=temperature,
        max_output_tokens=max_tokens,
        top_p=1.0,
        store=True
    )
    
    # Extract data from response
    response_text = extract_response_text(response)
    citations = extract_citations(response) if enable_web_search else []
    
    # Try to parse JSON from response
    parsed_json = parse_json_from_response(response_text)
    
    return {
        "text": response_text,
        "citations": citations,
        "json": parsed_json,
        "model": response.model,
        "status": response.status
    }
