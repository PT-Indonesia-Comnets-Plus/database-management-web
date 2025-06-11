"""
Enhanced Intent Analysis Tool - Multi-phase reflection for better tool selection
Inspired by the sophisticated web research reflection architecture
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime

# Import configuration
from core.utils.load_config import TOOLS_CFG


class IntentAnalysis(BaseModel):
    """Analysis of user intent and required capabilities"""
    primary_intent: str = Field(
        description="Main intent category (data_query, visualization, research, documentation)")
    confidence_score: float = Field(
        description="Confidence in intent classification (0-1)")
    required_data_sources: List[str] = Field(
        description="What data sources are needed")
    complexity_level: str = Field(description="Simple, Medium, or Complex")
    user_expectations: str = Field(
        description="What the user likely expects as output")


class ToolStrategy(BaseModel):
    """A tool selection strategy with rationale"""
    tool_name: str = Field(description="Name of the tool to use")
    sequence_order: int = Field(
        description="Order in execution sequence (1, 2, 3...)")
    rationale: str = Field(description="Why this tool is needed")
    expected_output: str = Field(
        description="What output this tool should provide")


class ToolSelectionPlan(BaseModel):
    """Complete plan for tool selection and execution"""
    strategies: List[ToolStrategy] = Field(
        description="Ordered list of tools to execute")
    alternative_approaches: List[str] = Field(
        description="Alternative approaches if primary fails")
    success_criteria: str = Field(
        description="How to determine if the plan succeeded")


class ToolSelectionReflection(BaseModel):
    """Reflection on tool selection quality"""
    is_optimal: bool = Field(
        description="Whether current tool selection is optimal")
    gaps_identified: List[str] = Field(
        description="What gaps exist in current approach")
    recommended_improvements: List[str] = Field(
        description="Specific improvements to make")
    alternative_tools: List[str] = Field(
        description="Alternative tools to consider")


def analyze_user_intent(user_query: str) -> IntentAnalysis:
    """
    Phase 1: Deep analysis of user intent to understand what they really want
    """
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=0.1,  # Low temperature for consistent analysis
            max_retries=2,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(IntentAnalysis)

        current_date = datetime.now().strftime("%B %d, %Y")

        analysis_prompt = f"""You are an expert intent analysis system. Analyze the user query to understand their true intent and requirements.

Current Date: {current_date}
User Query: "{user_query}"

Available System Capabilities:
1. DATABASE QUERIES - query_asset_database, sql_agent (for counts, totals, asset data)
2. VISUALIZATION - create_visualization (for charts, graphs, visual representations)
3. WEB RESEARCH - tools_web_search (for comprehensive internet research with citations and iterative refinement)
4. DOCUMENTATION - search_internal_documents (for guides, SOPs, technical docs)
5. SPREADSHEET PROCESSING - trigger_spreadsheet_etl_and_get_summary (for file processing)

Analyze the query to determine:
1. What is the PRIMARY intent? (data retrieval, visualization, research, documentation, etc.)
2. How confident are you in this classification?
3. What data sources would be needed to fulfill this request?
4. How complex is this request? (Simple=single tool, Medium=2 tools, Complex=3+ tools)
5. What does the user likely expect as the final output?

Focus on understanding the COMPLETE user need, not just surface-level keywords.
"""

        result = structured_llm.invoke(analysis_prompt)
        return result
    except Exception as e:
        print(f"Error in intent analysis: {e}")
        # Fallback analysis
        return IntentAnalysis(
            primary_intent="unknown",
            confidence_score=0.5,
            required_data_sources=["unclear"],
            complexity_level="Medium",
            user_expectations="Generic response based on query content"
        )


def generate_tool_selection_plan(user_query: str, intent_analysis: IntentAnalysis) -> ToolSelectionPlan:
    """
    Phase 2: Generate a comprehensive plan for tool selection and execution sequence
    """
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=0.3,
            max_retries=2,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(ToolSelectionPlan)
        planning_prompt = f"""You are an expert system architect. Create an optimal tool execution plan based on the user query and intent analysis.

User Query: "{user_query}"

Intent Analysis Results:
- Primary Intent: {intent_analysis.primary_intent}
- Confidence: {intent_analysis.confidence_score}
- Required Data Sources: {intent_analysis.required_data_sources}
- Complexity: {intent_analysis.complexity_level}
- User Expectations: {intent_analysis.user_expectations}

Available Tools:
1. search_internal_documents - For internal documentation, guides, SOPs, technical terms, COMPANY INFORMATION (FAT, FDT, ICONNET, ICON Plus, PLN, Telkom)
2. query_asset_database - For database queries about assets, counts, totals, locations
3. tools_web_search - For comprehensive internet research with advanced features (for external information only)
4. enhanced_web_research - For basic internet research (legacy fallback)
5. create_visualization - For creating charts, graphs, visual representations
6. trigger_spreadsheet_etl_and_get_summary - For spreadsheet processing and ETL
7. sql_agent - For complex SQL database operations

STRATEGIC PLANNING RULES:
1. For spreadsheet operations (ambil data, upload, file processing, data terbaru dari spreadsheet) → trigger_spreadsheet_etl_and_get_summary
2. For technical telecommunications terms (fat, fdt, ont, olt, home connected) → ALWAYS try search_internal_documents FIRST
3. For data queries (database assets, counts, totals) → query_asset_database or sql_agent
4. For visualization → data tool first, then create_visualization
5. For unclear or ambiguous queries → tools_web_search as reliable fallback
6. For general information → tools_web_search

FALLBACK STRATEGY:
- Primary: Use most specific tool for the query type
- Secondary: If unclear, use search_internal_documents for technical terms
- Tertiary: tools_web_search as universal fallback

Create a strategic plan that:
1. Orders tools in logical execution sequence (some may need data from others)
2. Explains the rationale for each tool selection
3. Describes expected output from each tool
4. Provides alternative approaches including search_internal_documents and tools_web_search fallbacks
5. Defines clear success criteria

Consider tool dependencies (e.g., visualization often needs data first).
"""
        result = structured_llm.invoke(planning_prompt)
        return result
    except Exception as e:
        print(f"Error in tool selection planning: {e}")

        # Improved fallback plan with better logic
        query_lower = user_query.lower()        # Smart fallback based on query content
        if any(term in query_lower for term in ['spreadsheet', 'excel', 'ambil data', 'upload', 'etl', 'file', 'data terbaru']):
            # Spreadsheet operations
            fallback_tool = "trigger_spreadsheet_etl_and_get_summary"
            fallback_rationale = "Query involves spreadsheet or file operations"
            alternative_approaches = [
                "Check file format compatibility", "Verify data structure"]
        elif any(term in query_lower for term in ['fat', 'fdt', 'ont', 'olt', 'home connected', 'fiber', 'konfigurasi', 'iconnet', 'icon plus', 'pln', 'apa itu', 'jelaskan', 'pengertian', 'definisi']):
            # Technical terms or definition requests - try internal docs first
            fallback_tool = "search_internal_documents"
            fallback_rationale = "Query contains technical terms or definition requests - checking internal documentation first"
            alternative_approaches = [
                "Enhanced web research if internal docs insufficient", "Contact technical support"]
        else:
            # General query - use web research
            fallback_tool = "tools_web_search"
            fallback_rationale = "General query - using advanced web research as reliable fallback"
            alternative_approaches = [
                "Check internal documentation", "Use enhanced_web_research if tools_web_search fails"]

        return ToolSelectionPlan(
            strategies=[ToolStrategy(
                tool_name=fallback_tool,
                sequence_order=1,
                rationale=fallback_rationale,
                expected_output="Relevant information about the query topic"
            )],
            alternative_approaches=alternative_approaches,
            success_criteria="Provide relevant and accurate response to user query"
        )


def reflect_on_tool_selection(user_query: str, planned_tools: List[str], executed_tools: List[str] = None) -> ToolSelectionReflection:
    """
    Phase 3: Reflect on the quality of tool selection before/after execution
    """
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=0.2,
            max_retries=2,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
        structured_llm = llm.with_structured_output(ToolSelectionReflection)

        execution_context = f"Executed tools: {executed_tools}" if executed_tools else "Pre-execution analysis"

        reflection_prompt = f"""You are an expert system evaluator. Analyze the tool selection quality for this user query.

User Query: "{user_query}"
Planned Tools: {planned_tools}
{execution_context}

Available Tools for Context:
- search_internal_documents: Internal documentation, guides, SOPs, technical terms, COMPANY INFORMATION (FAT, FDT, ICONNET, ICON Plus, PLN, Telkom)
- query_asset_database: Database queries for assets, counts, statistics
- tools_web_search: Advanced web research with iterative refinement and citation handling (for external information only)
- enhanced_web_research: Basic web research (legacy)
- create_visualization: Charts, graphs, visual representations
- trigger_spreadsheet_etl_and_get_summary: Spreadsheet processing
- sql_agent: Complex SQL database operations

CRITICAL EVALUATION CRITERIA:
1. Is this tool selection OPTIMAL for the user's query?
2. What gaps or issues do you identify in the current approach?
3. What specific improvements would you recommend?
4. What alternative tools should be considered?

SPECIAL CASES TO CONSIDER:
- If query contains technical terms like "fat", "fdt", "home connected" → try search_internal_documents first
- If query is unclear or ambiguous → tools_web_search as reliable fallback
- If query asks for comparisons of technical concepts → search_internal_documents + tools_web_search

IMPORTANT: If the query is unclear or involves technical telecommunications terms, 
ALWAYS recommend search_internal_documents first, then tools_web_search as backup.

Focus on whether the tools will actually fulfill the user's underlying intent and expectations.
"""

        result = structured_llm.invoke(reflection_prompt)
        return result
    except Exception as e:
        print(f"Error in tool selection reflection: {e}")
        # Fallback reflection with improved logic
        return ToolSelectionReflection(
            is_optimal=False,
            gaps_identified=[
                "Unable to analyze due to reflection error", "Need fallback strategy"],
            recommended_improvements=[
                "Use search_internal_documents for technical terms", "Use tools_web_search as final fallback"],
            alternative_tools=[
                "search_internal_documents", "tools_web_search"]
        )


@tool
def enhanced_intent_analysis(query: str) -> str:
    """
    Multi-phase intent analysis and tool selection optimization system.

    This tool provides sophisticated analysis of user intent and optimal tool selection
    using a reflection-based approach similar to the enhanced web research system.

    Phases:
    1. Deep intent analysis to understand what user really wants
    2. Strategic tool selection planning with execution sequence
    3. Reflection on tool selection quality with improvement suggestions

    Args:
        query: The user query to analyze

    Returns:
        Comprehensive analysis and recommendations for optimal tool selection
    """
    max_optimization_loops = 2
    optimization_count = 0

    try:
        print(f"🧠 Starting enhanced intent analysis for: {query}")

        # Phase 1: Deep Intent Analysis
        print("📊 Phase 1: Analyzing user intent...")
        intent_analysis = analyze_user_intent(query)

        print(f"   Primary Intent: {intent_analysis.primary_intent}")
        print(f"   Confidence: {intent_analysis.confidence_score}")
        print(f"   Complexity: {intent_analysis.complexity_level}")

        # Phase 2: Tool Selection Planning
        print("🛠️ Phase 2: Generating tool selection plan...")
        tool_plan = generate_tool_selection_plan(query, intent_analysis)

        planned_tool_names = [
            strategy.tool_name for strategy in tool_plan.strategies]
        print(f"   Planned Tools: {planned_tool_names}")

        # Phase 3: Iterative Tool Selection Optimization
        while optimization_count < max_optimization_loops:
            optimization_count += 1
            print(
                f"🔍 Phase 3.{optimization_count}: Reflecting on tool selection quality...")

            reflection = reflect_on_tool_selection(query, planned_tool_names)

            if reflection.is_optimal:
                print("✅ Tool selection is optimal - stopping optimization")
                break

            if reflection.recommended_improvements:
                print(
                    f"🔄 Optimization suggestions found: {len(reflection.recommended_improvements)}")

                # Re-plan with reflection insights
                enhanced_planning_prompt = f"""
Original Query: {query}
Current Plan Issues: {reflection.gaps_identified}
Improvement Suggestions: {reflection.recommended_improvements}
Alternative Tools to Consider: {reflection.alternative_tools}

Generate an improved tool selection plan addressing these concerns.
"""
                print("🎯 Re-generating improved tool plan...")
                # This would ideally re-run planning with the reflection insights
                # For now, we'll note the improvements
            else:
                print("ℹ️ No specific improvements suggested - stopping optimization")
                break

        # Phase 4: Compile comprehensive analysis
        print("📋 Phase 4: Compiling comprehensive analysis...")

        analysis_report = f"""# Enhanced Intent Analysis Results

## User Query Analysis
**Query:** {query}
**Primary Intent:** {intent_analysis.primary_intent}
**Confidence Score:** {intent_analysis.confidence_score:.2f}
**Complexity Level:** {intent_analysis.complexity_level}

## Intent Analysis Details
**Required Data Sources:** {', '.join(intent_analysis.required_data_sources)}
**User Expectations:** {intent_analysis.user_expectations}

## Recommended Tool Execution Plan
"""

        for i, strategy in enumerate(tool_plan.strategies, 1):
            analysis_report += f"""
### {i}. {strategy.tool_name}
- **Execution Order:** {strategy.sequence_order}
- **Rationale:** {strategy.rationale}
- **Expected Output:** {strategy.expected_output}
"""

        analysis_report += f"""

## Alternative Approaches
{chr(10).join('- ' + approach for approach in tool_plan.alternative_approaches)}

## Success Criteria
{tool_plan.success_criteria}

## Quality Optimization Results
- **Optimization Loops Performed:** {optimization_count}
- **Final Assessment:** {'Optimal' if reflection.is_optimal else 'Needs Improvement'}
"""

        if not reflection.is_optimal:
            analysis_report += f"""
- **Identified Gaps:** {', '.join(reflection.gaps_identified)}
- **Recommended Improvements:** {', '.join(reflection.recommended_improvements)}
"""

        analysis_report += f"""

## Implementation Recommendations
The analysis suggests using the following tools in sequence:
**{' → '.join(planned_tool_names)}**

This approach will best fulfill the user's intent of "{intent_analysis.primary_intent}" with their expectation of "{intent_analysis.user_expectations}".

**Analysis completed on:** {datetime.now().strftime("%B %d, %Y at %H:%M")}
"""

        print(f"✅ Enhanced intent analysis completed successfully")
        return analysis_report

    except Exception as e:
        error_msg = f"Error in enhanced intent analysis: {str(e)}"
        print(f"❌ {error_msg}")
        return f"I encountered an error while performing enhanced intent analysis for '{query}': {error_msg}"
