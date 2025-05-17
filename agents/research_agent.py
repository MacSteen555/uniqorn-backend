import os
from typing import List, Any
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool

# Import all your tools
from tools.firecrawl_tools import firecrawl_search_tool, firecrawl_fetch_tool
from tools.newsapi import news_tool
from tools.producthunt import producthunt_tool
from tools.pytrends import trends_tool
from tools.reddit import reddit_tool

def create_research_agent(
    temperature: float = 0.1,
    model: str = "gpt-4.1-mini",
    streaming: bool = True,
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
    )
    
    # Create a prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a research assistant with access to various tools to gather information.
        Your goal is to provide comprehensive, accurate, and up-to-date information based on the user's query.
        Use the appropriate tools to gather the most relevant information.
        
        When using search tools, try to be specific with your queries.
        When fetching content, analyze it carefully and extract the most relevant information.
        
        Always cite your sources when providing information."""),
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
    )
    
    return agent_executor

# Example usage
if __name__ == "__main__":
    agent = create_research_agent()
    result = agent.invoke({"input": "What are the latest trends in AI startups?"})
    print(result["output"])
