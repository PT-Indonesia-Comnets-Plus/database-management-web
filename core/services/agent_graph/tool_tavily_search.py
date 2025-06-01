from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from ...utils.load_config import TOOLS_CFG


def load_tavily_search_tool(tavily_search_max_results: int):
    """
    This function initializes a Tavily search tool, which performs searches and returns results
    based on user queries. The `max_results` parameter controls how many search results are
    retrieved for each query.

    Args:
        tavily_search_max_results (int): The maximum number of search results to return for each query.

    Returns:
        TavilySearchResults: A configured instance of the Tavily search tool with the specified `max_results`.
    """
    return TavilySearchResults(max_results=tavily_search_max_results)


@tool
def tavily_web_search(query: str) -> str:
    """
    Search the web for current information using Tavily search.

    Args:
        query (str): Search query for web search

    Returns:
        str: Search results from the web
    """
    try:
        tavily_tool = load_tavily_search_tool(
            TOOLS_CFG.tavily_search_max_results)
        results = tavily_tool.invoke({"query": query})
        return str(results)
    except Exception as e:
        return f"Web search error: {str(e)}"
