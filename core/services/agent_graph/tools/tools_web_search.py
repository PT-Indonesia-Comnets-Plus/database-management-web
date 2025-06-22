"""
Tools Web Search - Tavily-Compatible Implementation
Uses Tavily for web search while maintaining the exact same architecture 
and workflow as the backend project for robust research capabilities.
"""

import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime

# Import Tavily for web search
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

# Import configuration
from core.utils.load_config import TOOLS_CFG


# Backend-compatible Pydantic Models
class SearchQueryList(BaseModel):
    """Multiple search queries - exact backend format"""
    query: List[str] = Field(description="List of search queries")


class Reflection(BaseModel):
    """Reflection on search results - exact backend format"""
    is_sufficient: bool = Field(description="Whether results are sufficient")
    knowledge_gap: str = Field(description="What information is missing")
    follow_up_queries: List[str] = Field(
        description="Additional queries needed")


# Utility Functions from Backend
def get_current_date() -> str:
    """Get current date in readable format"""
    return datetime.now().strftime("%B %d, %Y")


def get_research_topic(messages) -> str:
    """Extract research topic from messages"""
    try:
        if isinstance(messages, str):
            return messages
        elif isinstance(messages, list) and messages:
            # Get the last human message content
            for message in reversed(messages):
                if hasattr(message, 'content') and message.content:
                    return message.content
                elif isinstance(message, str):
                    return message
        return "General research topic"
    except Exception as e:
        print(f"Warning: Error extracting research topic: {e}")
        return "General research topic"


# Core Research Functions with Backend Architecture
def generate_query(research_topic: str) -> List[str]:
    """Generate search queries using backend's exact approach"""
    try:
        # Use backend's exact LLM configuration
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.query_generator_model,
            temperature=TOOLS_CFG.llm_temperature,
            max_retries=TOOLS_CFG.max_retries,
            max_tokens=500,
            api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(SearchQueryList)

        # Backend's exact query writer instructions
        current_date = get_current_date()
        query_writer_instructions = """You are a professional researcher. Decompose "{research_topic}" into {number_queries} search queries that will help me write a comprehensive article on the topic. 

Make the queries atomic and as specific as possible.

IMPORTANT:
- Only return the search queries, nothing else.
- If the research topic is asking questions about current events or recent information, make sure to include the current date ({current_date}) in your search queries.
- NEVER include phrases like "based on", "according to", "search for", etc. in your queries
- Keep each query under 10 words when possible

Context:
{research_topic}"""

        formatted_prompt = query_writer_instructions.format(
            research_topic=research_topic,
            number_queries=TOOLS_CFG.number_of_initial_queries,
            current_date=current_date,
        )

        result = structured_llm.invoke(formatted_prompt)
        return result.query

    except Exception as e:
        print(f"Query generation error: {e}")
        return [research_topic]


def web_research(search_query: str, query_id: int = 0) -> Dict[str, Any]:
    """Perform web research using Tavily API"""
    try:
        # Check if Tavily is available and configured
        if TavilyClient is None:
            raise ImportError("Tavily client not available")

        if not hasattr(TOOLS_CFG, 'tavily_api_key') or not TOOLS_CFG.tavily_api_key:
            raise ValueError("Tavily API key not configured")

        # Initialize Tavily client
        tavily_client = TavilyClient(api_key=TOOLS_CFG.tavily_api_key)

        # Perform search using Tavily
        search_result = tavily_client.search(
            query=search_query,
            max_results=TOOLS_CFG.tavily_max_results,
            include_domains=None,
            exclude_domains=None,
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )

        # Process Tavily results to match backend format
        sources_gathered = []
        web_research_result = []

        if search_result and 'results' in search_result:
            # Create summary from search results
            summary_parts = []

            for idx, result in enumerate(search_result['results']):
                title = result.get('title', 'Source')
                url = result.get('url', '')
                content = result.get('content', '')

                if content:
                    summary_parts.append(f"**{title}**: {content}")

                # Add to sources in backend-compatible format
                sources_gathered.append({
                    "label": title,
                    "short_url": f"https://tavily.com/id/{query_id}-{idx}",
                    "value": url,
                })

            # Create research summary
            if summary_parts:
                research_summary = "\n\n".join(summary_parts)
            else:
                research_summary = f"Search completed for: {search_query}"

            # Add Tavily's answer if available
            if search_result.get('answer'):
                research_summary = f"{search_result['answer']}\n\n{research_summary}"

            web_research_result = [research_summary]

        else:
            web_research_result = [
                f"No detailed results found for: {search_query}"]

        return {
            "sources_gathered": sources_gathered,
            "search_query": [search_query],
            "web_research_result": web_research_result,
        }

    except ImportError:
        print(f"Tavily not available, using fallback for: {search_query}")
        return {
            "sources_gathered": [],
            "search_query": [search_query],
            "web_research_result": [f"Web search unavailable for: {search_query}. Please install tavily-python package."],
        }

    except ValueError as e:
        print(f"Configuration error: {e}")
        return {
            "sources_gathered": [],
            "search_query": [search_query],
            "web_research_result": [f"Configuration error for search: {search_query}. {str(e)}"],
        }

    except Exception as e:
        print(f"Tavily search error for '{search_query}': {e}")

        # Handle rate limiting gracefully
        if "rate limit" in str(e).lower() or "429" in str(e):
            return {
                "sources_gathered": [],
                "search_query": [search_query],
                "web_research_result": [f"Rate limit reached for: {search_query}. Please try again later."],
            }

        return {
            "sources_gathered": [],
            "search_query": [search_query],
            "web_research_result": [f"Unable to search for: {search_query}. Error: {str(e)}"],
        }


def reflection(research_topic: str, web_research_results: List[str]) -> Reflection:
    """Perform reflection using backend's exact approach"""
    try:
        # Use backend's exact reflection model
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.llm_reflection_model,
            temperature=TOOLS_CFG.llm_temperature,
            max_retries=TOOLS_CFG.max_retries,
            api_key=TOOLS_CFG.gemini_api_key,
        )

        # Backend's exact reflection instructions
        current_date = get_current_date()
        reflection_instructions = """You are an expert research assistant analyzing summaries about "{research_topic}".

Your task: Evaluate if the research results provide sufficient coverage of the topic and identify any knowledge gaps.

Current Date: {current_date}
Research Topic: {research_topic}

Research Summaries:
{summaries}

Analyze these summaries and determine:
1. Are the key questions answered comprehensively?
2. Is the information current and accurate?
3. Are there significant gaps in coverage?
4. What additional information would improve the research?

If the research is insufficient, suggest specific follow-up queries that would address the knowledge gaps.
Limit follow-up queries to maximum 2 highly focused searches.

Provide your analysis in the requested format focusing on completeness and quality of information."""

        formatted_prompt = reflection_instructions.format(
            current_date=current_date,
            research_topic=research_topic,
            summaries="\n\n---\n\n".join(web_research_results),
        )

        result = llm.with_structured_output(
            Reflection).invoke(formatted_prompt)
        return result

    except Exception as e:
        print(f"Reflection error: {e}")
        return Reflection(
            is_sufficient=True,
            knowledge_gap="Analysis unavailable due to technical error",
            follow_up_queries=[]
        )


@tool
def tools_web_search(query: str) -> str:
    """
    Advanced web research tool using Tavily API with backend-compatible architecture.

    Uses Tavily for robust web search while maintaining the exact same workflow 
    as the sophisticated backend research system:
    - Professional query generation with atomic, specific searches
    - Tavily API for comprehensive web search with source tracking
    - Intelligent reflection to identify knowledge gaps
    - Iterative research with follow-up queries when needed
    - Comprehensive result formatting with proper citations

    Optimized for research quality and reliability.

    Args:
        query: The research topic or question to investigate

    Returns:
        Comprehensive research results with citations and sources
    """
    try:
        print(f"🔍 Starting Tavily-powered web research for: {query}")

        # Backend-style state tracking
        state = {
            "messages": [query],
            "search_query": [],
            "web_research_result": [],
            "sources_gathered": [],
            "research_loop_count": 0
        }

        # Phase 1: Generate queries (backend approach)
        print("📝 Generating search queries...")
        search_queries = generate_query(query)
        print(f"Generated {len(search_queries)} search queries")

        # Phase 2: Execute searches using Tavily
        print("🌐 Executing web research with Tavily...")
        for i, search_query in enumerate(search_queries):
            try:
                result = web_research(search_query, i)
                state["search_query"].extend(result["search_query"])
                state["web_research_result"].extend(
                    result["web_research_result"])
                state["sources_gathered"].extend(result["sources_gathered"])

            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    print("⚠️ Tavily rate limit reached - using collected results")
                    break
                print(f"Search error: {e}")
                continue

        # Phase 3: Reflection (backend approach)
        if state["web_research_result"] and state["research_loop_count"] < TOOLS_CFG.max_research_loops:
            print("🤔 Analyzing research completeness...")
            state["research_loop_count"] += 1

            try:
                reflection_result = reflection(
                    query, state["web_research_result"])

                # Follow-up research if needed
                if (not reflection_result.is_sufficient and
                    reflection_result.follow_up_queries and
                        len(reflection_result.follow_up_queries) > 0):

                    print("🔄 Performing follow-up research...")
                    # Only one follow-up to manage API usage
                    follow_up_query = reflection_result.follow_up_queries[0]

                    try:
                        result = web_research(
                            follow_up_query, len(state["search_query"]))
                        state["search_query"].extend(result["search_query"])
                        state["web_research_result"].extend(
                            result["web_research_result"])
                        state["sources_gathered"].extend(
                            result["sources_gathered"])

                    except Exception as e:
                        if "rate limit" in str(e).lower() or "429" in str(e):
                            print("⚠️ Rate limit reached during follow-up")
                        else:
                            print(f"Follow-up error: {e}")

            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    print("⚠️ Rate limit reached during reflection")
                else:
                    print(f"Reflection error: {e}")

        # Phase 4: Finalize results (backend approach)
        print("📊 Finalizing research results...")

        if not state["web_research_result"]:
            return f"⚠️ Unable to complete research due to API limitations. Please try again later for: {query}"

        # Format results with backend-style comprehensive output
        final_content = f"# Research Results: {query}\n\n"

        final_content += "## Executive Summary\n\n"
        final_content += f"Comprehensive research conducted using {len(state['search_query'])} targeted search queries across {state['research_loop_count']} research iterations.\n\n"

        final_content += "## Research Findings\n\n"
        final_content += "\n\n---\n\n".join(state["web_research_result"])

        # Add sources with proper formatting
        if state["sources_gathered"]:
            final_content += "\n\n## Sources and References\n\n"

            # Deduplicate sources
            unique_sources = []
            seen_urls = set()

            for source in state["sources_gathered"]:
                url = source.get("value", "")
                if url and url not in seen_urls:
                    unique_sources.append(source)
                    seen_urls.add(url)

            for i, source in enumerate(unique_sources, 1):
                title = source.get('label', 'Source')
                url = source.get('value', '#')
                final_content += f"{i}. [{title}]({url})\n"

        # Add metadata
        final_content += f"\n\n## Research Metadata\n"
        final_content += f"- **Queries executed:** {len(state['search_query'])}\n"
        final_content += f"- **Research iterations:** {state['research_loop_count']}\n"
        final_content += f"- **Sources found:** {len(unique_sources) if state['sources_gathered'] else 0}\n"
        final_content += f"- **Research completed:** {get_current_date()}\n"
        final_content += f"- **Search engine:** Tavily API\n"

        print("✅ Tavily-powered research completed successfully")
        return final_content

    except Exception as e:
        error_msg = f"Research error: {str(e)}"
        print(f"❌ {error_msg}")

        if "rate limit" in str(e).lower() or "429" in str(e):
            return f"⚠️ API rate limit exceeded during research for '{query}'. Please try again later."

        return f"I encountered an error during research for '{query}': {error_msg}"
