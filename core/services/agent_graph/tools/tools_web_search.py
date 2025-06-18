"""
Tools Web Search - Backend-Compatible Implementation
Uses the exact same architecture and configuration as the backend project
for optimal quota efficiency and robust research capabilities.
"""

import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
from google.genai import Client

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
    if isinstance(messages, str):
        return messages
    elif isinstance(messages, list) and messages:
        # Get the last human message content
        for message in reversed(messages):
            if hasattr(message, 'content'):
                return message.content
            elif isinstance(message, str):
                return message
    return "General research topic"


def resolve_urls(grounding_chunks: List[Any], id: int) -> Dict[str, str]:
    """Create short URLs map - exact backend implementation"""
    prefix = f"https://vertexaisearch.cloud.google.com/id/"
    urls = []

    for chunk in grounding_chunks:
        if hasattr(chunk, 'web') and hasattr(chunk.web, 'uri'):
            urls.append(chunk.web.uri)

    resolved_map = {}
    for idx, url in enumerate(urls):
        if url not in resolved_map:
            resolved_map[url] = f"{prefix}{id}-{idx}"

    return resolved_map


def get_citations(response, resolved_urls_map: Dict[str, str]) -> List[Dict]:
    """Extract citations from response - exact backend implementation"""
    citations = []

    if not response or not response.candidates:
        return citations

    candidate = response.candidates[0]
    if (not hasattr(candidate, "grounding_metadata") or
        not candidate.grounding_metadata or
            not hasattr(candidate.grounding_metadata, "grounding_supports")):
        return citations

    for support in candidate.grounding_metadata.grounding_supports:
        citation = {}

        if not hasattr(support, "segment") or support.segment is None:
            continue

        start_index = (support.segment.start_index
                       if support.segment.start_index is not None else 0)

        if support.segment.end_index is None:
            continue

        citation["start_index"] = start_index
        citation["end_index"] = support.segment.end_index
        citation["segments"] = []

        if (hasattr(support, "grounding_chunk_indices") and
                support.grounding_chunk_indices):
            for ind in support.grounding_chunk_indices:
                try:
                    chunk = candidate.grounding_metadata.grounding_chunks[ind]
                    resolved_url = resolved_urls_map.get(chunk.web.uri, None)

                    title = "Source"
                    if hasattr(chunk.web, 'title') and chunk.web.title:
                        title = chunk.web.title.split(
                            ".")[0] if "." in chunk.web.title else chunk.web.title

                    citation["segments"].append({
                        "label": title,
                        "short_url": resolved_url,
                        "value": chunk.web.uri,
                    })
                except (IndexError, AttributeError):
                    pass

        citations.append(citation)

    return citations


def insert_citation_markers(text: str, citations_list: List[Dict]) -> str:
    """Insert citation markers - exact backend implementation"""
    if not citations_list:
        return text

    # Sort citations by end_index in descending order
    sorted_citations = sorted(
        citations_list, key=lambda c: (c["end_index"], c["start_index"]), reverse=True
    )

    modified_text = text
    for citation_info in sorted_citations:
        end_idx = citation_info["end_index"]
        marker_to_insert = ""
        for segment in citation_info["segments"]:
            marker_to_insert += f" [{segment['label']}]({segment['short_url']})"
        modified_text = (
            modified_text[:end_idx] +
            marker_to_insert + modified_text[end_idx:]
        )

    return modified_text


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
    """Perform web research using backend's exact approach"""
    try:
        # Initialize client exactly as backend
        genai_client = Client(api_key=TOOLS_CFG.gemini_api_key)

        # Backend's exact web searcher instructions
        current_date = get_current_date()
        web_searcher_instructions = """Conduct targeted Google Searches to gather the most recent, credible information on "{research_topic}" and synthesize it into a verifiable text artifact.

Instructions:
- Query should ensure that the most current information is gathered. The current date is {current_date}.
- Conduct multiple, diverse searches to gather comprehensive information.
- Consolidate key findings while meticulously tracking the source(s) for each specific piece of information.
- The output should be a well-written summary or report based on your search findings. 
- Only include the information found in the search results, don't make up any information.

Research Topic:
{research_topic}"""

        formatted_prompt = web_searcher_instructions.format(
            current_date=current_date,
            research_topic=search_query,
        )

        # Use exact same API call as backend
        response = genai_client.models.generate_content(
            model=TOOLS_CFG.query_generator_model,
            contents=formatted_prompt,
            config={
                "tools": [{"google_search": {}}],
                "temperature": 0,
            },
        )

        # Process exactly as backend does
        resolved_urls = resolve_urls(
            response.candidates[0].grounding_metadata.grounding_chunks, query_id
        )
        citations = get_citations(response, resolved_urls)
        modified_text = insert_citation_markers(response.text, citations)
        sources_gathered = [
            item for citation in citations for item in citation["segments"]]

        return {
            "sources_gathered": sources_gathered,
            "search_query": [search_query],
            "web_research_result": [modified_text],
        }

    except Exception as e:
        print(f"Web research error for '{search_query}': {e}")
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
    Backend-compatible advanced web research tool with optimal quota efficiency.

    Uses the exact same architecture as the sophisticated backend research system:
    - Professional query generation with atomic, specific searches
    - Native Google Search API with grounding metadata
    - Citation handling with URL resolution and source tracking  
    - Intelligent reflection to identify knowledge gaps
    - Iterative research with follow-up queries when needed
    - Comprehensive result formatting with proper citations

    Optimized for quota efficiency while maintaining research quality.

    Args:
        query: The research topic or question to investigate

    Returns:
        Comprehensive research results with citations and sources
    """
    try:
        print(f"🔍 Starting backend-compatible web research for: {query}")

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

        # Phase 2: Execute searches (backend parallel approach simulation)
        print("🌐 Executing web research...")
        for i, search_query in enumerate(search_queries):
            try:
                result = web_research(search_query, i)
                state["search_query"].extend(result["search_query"])
                state["web_research_result"].extend(
                    result["web_research_result"])
                state["sources_gathered"].extend(result["sources_gathered"])

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("⚠️ API quota reached - using collected results")
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

                # Follow-up research if needed (limited for quota efficiency)
                if (not reflection_result.is_sufficient and
                    reflection_result.follow_up_queries and
                        len(reflection_result.follow_up_queries) > 0):

                    print("🔄 Performing follow-up research...")
                    # Only one follow-up
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
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            print("⚠️ Quota limit reached during follow-up")
                        else:
                            print(f"Follow-up error: {e}")

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("⚠️ Quota limit reached during reflection")
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
        final_content += f"- **Architecture:** Backend-compatible iterative research\n"

        print("✅ Backend-compatible research completed successfully")
        return final_content

    except Exception as e:
        error_msg = f"Research error: {str(e)}"
        print(f"❌ {error_msg}")

        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            return f"⚠️ API quota exceeded during research for '{query}'. Please try again later."

        return f"I encountered an error during research for '{query}': {error_msg}"
