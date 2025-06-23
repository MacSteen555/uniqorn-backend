import os
from typing import List, Optional, Any
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.callbacks.base import BaseCallbackHandler

from tools.firecrawl_tools import firecrawl_search_tool, firecrawl_fetch_tool
from tools.newsapi import news_tool
from tools.producthunt import producthunt_tool
from tools.pytrends import trends_tool
from tools.reddit import reddit_tool

def create_research_agent(
    temperature: float = 0.7,
    model: str = "gpt-4.1-mini",
    streaming: bool = True,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> AgentExecutor:
    """Create a research agent with access to all tools."""
    
    # Collect all tools
    tools: List[BaseTool] = [
        firecrawl_search_tool,
        firecrawl_fetch_tool,
        news_tool,
        producthunt_tool, 
        trends_tool,
        reddit_tool,
    ]
    
    # Create the LLM
    llm = ChatOpenAI(
        temperature=temperature,
        model=model,
        streaming=streaming,
        api_key=os.getenv("OPENAI_API_KEY"),
        callbacks=callbacks,
    )
    
    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert startup advisor and idea builder. Your goal is to help entrepreneurs refine and develop their startup ideas through thoughtful questioning, market research, and practical advice.

INSTRUCTIONS:
1. UNDERSTAND THE IDEA: Ask clarifying questions to fully understand the core concept, target audience, and value proposition.

2. MARKET RESEARCH: Use your research tools and your own knowledge to gather relevant data about:
   - Market size and growth trends
   - Existing competitors (same or different product, going after the same audience, etc.) and their approaches
   - Existing parallel (similar product, similar business model, looking for a different audience, etc.) companies and their approaches
   - Customer pain points and needs
   - Recent news and developments in the space

3. IDEA REFINEMENT:
   - Help identify the most compelling unique value proposition
   - Suggest potential pivots or refinements based on market gaps
   - Identify potential challenges and how to address them
   - Recommend initial target customer segments

4. FEATURE PLANNING:
   - Help prioritize features for an MVP (Minimum Viable Product)
   - Analyze technical feasibility of proposed features
   - Suggest existing tools, APIs, or technologies that could accelerate development
   - Provide examples of similar implementations when relevant

5. GO-TO-MARKET STRATEGY:
   - Suggest channels for customer acquisition
   - Discuss potential business models and monetization approaches
   - Recommend initial metrics to track

Always be constructive and supportive while providing honest feedback. Use data from your research tools to back up your suggestions. When appropriate, provide specific examples of successful companies with similar approaches or technologies.

Remember that the entrepreneur is the domain expert - your role is to enhance their thinking, not replace it. Ask thoughtful questions that help them develop their own insights.

Communicate with the user in a friendly and engaging manner, looking for the best opportunities for their startup. YOU DO NOT NEED TO USE THE TOOLS TO ANSWER THE USER'S QUESTION. Feel free to use your own knowledge and information to help the user. Do whatever you need to do to help the user the best you can.

When discussing technical implementation, be practical and consider the constraints of early-stage startups (limited resources, need for speed, etc.).

Use the web_search tool to find current information, market data, competitor analysis, and recent developments in relevant industries.
         
Use Markdown for the "response" field: headers (#, ##), bold text (**), lists (-, 1.), quotes (>), code blocks (```), and in-line hyperlinks ([link text](url)).
"""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create the agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        return_intermediate_steps=True,
        callbacks=callbacks,
    )
    
    return agent_executor

# Example usage
if __name__ == "__main__":
    agent = create_research_agent()
    result = agent.invoke({"input": "I would like to build a startup that helps people learn to code, where should I start? How should I go about it? I would like to utilize AI to do this. Is it a good idea? Who might compete with me? What are the best tools to use? What are the best resources to use?"})
    print(result["output"])
