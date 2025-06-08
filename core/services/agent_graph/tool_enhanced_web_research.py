"""
Enhanced Web Research Tool - Integrating backend's sophisticated research architecture
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
from datetime import datetime
import json

# Import configuration
from core.utils.load_config import TOOLS_CFG


class SearchQuery(BaseModel):
    """A single search query with rationale"""
    query: str = Field(description="The search query string")
    rationale: str = Field(description="Why this query is relevant")


class SearchQueryList(BaseModel):
    """Multiple search queries for comprehensive research"""
    queries: List[SearchQuery] = Field(
        description="List of optimized search queries")


class ReflectionResult(BaseModel):
    """Reflection on search results quality"""
    is_sufficient: bool = Field(description="Whether results are sufficient")
    knowledge_gap: str = Field(description="What information is missing")
    follow_up_queries: List[str] = Field(
        description="Additional queries needed")


class WebResearchResult(BaseModel):
    """Complete web research result with citations"""
    content: str = Field(description="Research content with citations")
    sources: List[Dict[str, str]] = Field(
        description="Source URLs and metadata")
    search_queries_used: List[str] = Field(
        description="Queries that were executed")


def get_current_date() -> str:
    """Get current date in readable format"""
    return datetime.now().strftime("%B %d, %Y")


def generate_search_queries(research_topic: str, num_queries: int = 3) -> List[SearchQuery]:
    """Generate optimized search queries for a research topic"""
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=1.0,
            max_retries=2,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(SearchQueryList)

        current_date = get_current_date()
        prompt = f"""You are an expert research assistant tasked with generating search queries for comprehensive web research.

Current Date: {current_date}
Research Topic: {research_topic}

Generate {num_queries} optimized search queries that will help gather comprehensive information about this topic. Each query should:
1. Target different aspects or angles of the research topic
2. Use effective search terms and operators
3. Be specific enough to get relevant results
4. Cover both current and historical information if relevant

Focus on creating queries that will give diverse, high-quality results from authoritative sources.
"""
        result = structured_llm.invoke(prompt)
        return result.queries
    except Exception as e:
        print(f"Error generating search queries: {e}")
        # Fallback to simple query
        return [SearchQuery(query=research_topic, rationale="Direct search for the topic")]


def perform_google_search(query: str, query_id: int = 0) -> Dict[str, Any]:
    """Perform Google search using Gemini's native search capability"""
    try:
        # Initialize Google GenAI client
        genai_client = Client(api_key=TOOLS_CFG.gemini_api_key)

        current_date = get_current_date()
        search_prompt = f"""Research the following topic thoroughly using web search:

Research Topic: {query}
Current Date: {current_date}

Please provide a comprehensive summary of the most current and relevant information about this topic. Include:
1. Key facts and findings
2. Recent developments or news
3. Authoritative sources and expert opinions
4. Context and background information

Focus on accuracy and cite reliable sources. If the topic involves recent events, prioritize the most up-to-date information.
"""

        response = genai_client.models.generate_content(
            model=TOOLS_CFG.primary_agent_llm,
            contents=search_prompt,
            config={
                "tools": [{"google_search": {}}],
                "temperature": 0,
            },
        )

        # Extract content and sources
        content = response.text
        sources = []

        # Extract grounding metadata if available
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                for chunk in candidate.grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        sources.append({
                            "url": chunk.web.uri,
                            "title": getattr(chunk.web, 'title', 'Unknown'),
                            "id": f"source-{query_id}-{len(sources)}"
                        })

        return {
            "content": content,
            "sources": sources,
            "query": query
        }
    except Exception as e:
        print(f"Error performing Google search for '{query}': {e}")
        return {
            "content": f"Unable to search for information about: {query}",
            "sources": [],
            "query": query
        }


def reflect_on_results(research_topic: str, search_results: List[Dict[str, Any]]) -> ReflectionResult:
    """Analyze search results to identify knowledge gaps"""
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=1.0,
            max_retries=2,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(ReflectionResult)

        current_date = get_current_date()
        combined_results = "\n\n---\n\n".join([result["content"]
                                              for result in search_results])

        reflection_prompt = f"""You are an expert research analyst. Analyze the following research results to determine if they sufficiently answer the research question.

Current Date: {current_date}
Research Topic: {research_topic}

Research Results:
{combined_results}

Evaluate whether these results provide comprehensive coverage of the research topic. Consider:
1. Are the key questions answered?
2. Is the information current and accurate?
3. Are there significant gaps in coverage?
4. What additional information would improve the research?

If the research is insufficient, suggest specific follow-up queries that would address the knowledge gaps.
"""

        result = structured_llm.invoke(reflection_prompt)
        return result
    except Exception as e:
        print(f"Error in reflection: {e}")
        return ReflectionResult(
            is_sufficient=True,
            knowledge_gap="Unable to analyze results",
            follow_up_queries=[]
        )


@tool
def enhanced_web_research(query: str) -> str:
    """
    Perform comprehensive web research using dynamic query generation, Google Search integration,
    and iterative refinement based on result quality analysis.

    This tool provides superior research capabilities compared to basic search by:
    - Generating multiple optimized search queries for comprehensive coverage
    - Using Google's native search API with grounding metadata
    - Analyzing results to identify knowledge gaps
    - Performing iterative searches to fill gaps
    - Providing properly cited results with source links

    Args:
        query: The research topic or question to investigate

    Returns:
        Comprehensive research results with citations and sources
    """
    max_research_loops = 2
    research_loop_count = 0
    all_results = []
    all_sources = []
    all_queries_used = []

    try:
        print(f"🔍 Starting enhanced web research for: {query}")

        # Phase 1: Generate initial search queries
        print("📝 Generating optimized search queries...")
        search_queries = generate_search_queries(query, num_queries=3)

        # Phase 2: Execute initial searches
        print(f"🌐 Executing {len(search_queries)} initial searches...")
        for i, search_query in enumerate(search_queries):
            result = perform_google_search(search_query.query, i)
            all_results.append(result)
            all_sources.extend(result["sources"])
            all_queries_used.append(result["query"])

        # Phase 3: Reflection and iterative refinement
        while research_loop_count < max_research_loops:
            research_loop_count += 1
            print(
                f"🤔 Reflection loop {research_loop_count}/{max_research_loops}")

            reflection = reflect_on_results(query, all_results)

            if reflection.is_sufficient:
                print("✅ Research is sufficient - stopping iterations")
                break

            if reflection.follow_up_queries:
                print(
                    f"🔄 Performing {len(reflection.follow_up_queries)} follow-up searches...")
                # Limit to 2 follow-ups
                for follow_up_query in reflection.follow_up_queries[:2]:
                    result = perform_google_search(
                        follow_up_query, len(all_results))
                    all_results.append(result)
                    all_sources.extend(result["sources"])
                    all_queries_used.append(result["query"])
            else:
                print("ℹ️ No follow-up queries suggested - stopping iterations")
                break

        # Phase 4: Compile final comprehensive result
        print("📊 Compiling comprehensive research results...")

        # Combine all research content
        combined_content = f"# Research Results for: {query}\n\n"

        for i, result in enumerate(all_results, 1):
            combined_content += f"## Search Result {i}\n"
            combined_content += f"**Query:** {result['query']}\n\n"
            combined_content += result['content']
            combined_content += "\n\n---\n\n"

        # Add sources section
        if all_sources:
            combined_content += "## Sources\n\n"
            unique_sources = []
            seen_urls = set()

            for source in all_sources:
                if source.get("url") and source["url"] not in seen_urls:
                    unique_sources.append(source)
                    seen_urls.add(source["url"])

            for i, source in enumerate(unique_sources, 1):
                combined_content += f"{i}. [{source.get('title', 'Source')}]({source.get('url', '#')})\n"

        # Add metadata
        combined_content += f"\n\n**Research Statistics:**\n"
        combined_content += f"- Search queries executed: {len(all_queries_used)}\n"
        combined_content += f"- Research loops performed: {research_loop_count}\n"
        combined_content += f"- Unique sources found: {len(unique_sources) if all_sources else 0}\n"
        combined_content += f"- Research completed on: {get_current_date()}\n"

        print(f"✅ Enhanced web research completed successfully")
        return combined_content

    except Exception as e:
        error_msg = f"Error in enhanced web research: {str(e)}"
        print(f"❌ {error_msg}")
        return f"I encountered an error while performing enhanced web research for '{query}': {error_msg}"
