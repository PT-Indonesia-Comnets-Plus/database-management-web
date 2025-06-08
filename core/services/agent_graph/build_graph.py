# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\build_graph.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from .tool_sql_agent import query_asset_database, sql_agent
from .tool_rag import search_internal_documents
from .tools_web_search import tools_web_search
from .tool_intent_analysis import enhanced_intent_analysis
from .tool_visualization import create_visualization
from .tool_airflow_trigger import trigger_spreadsheet_etl_and_get_summary
from ...utils.load_config import TOOLS_CFG
from .agent_backend import State, BasicToolNode, route_tools, reflection_node, should_retry_or_finish
import streamlit as st


@st.cache_resource
def build_graph():
    """
    Build a LangGraph agent integrating LLM with RAG, SQL, and Tavily search tools.
    Version 2.0 - With final response generation support    Returns:
        graph: Compiled LangGraph agent with memory checkpointing.
    """
    print("Building Agent Graph v2.0...")

    try:
        primary_llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )
    except Exception as e:
        return None

    try:
        tools = [
            search_internal_documents,
            query_asset_database,
            sql_agent,
            tools_web_search,
            enhanced_intent_analysis,
            create_visualization,
            trigger_spreadsheet_etl_and_get_summary,
        ]
        primary_llm_with_tools = primary_llm.bind_tools(tools)
        print(f"Tools bound to LLM: {[tool.name for tool in tools]}")
    except Exception as e:
        st.error(f"Failed to load or bind tools: {e}")
        print(f"Failed to load or bind tools: {e}")
        return None

    def chatbot(state: State):
        """
        Node that runs the primary LLM agent with bound tools.
        Enhanced dengan reflection support dan retry guidance.
        Supports both tool execution and final response generation.

        Args:
            state (State): Current state containing conversation messages.

        Returns:
            dict: Updated messages after LLM invocation.
        """
        print("Calling Chatbot Node...")
        current_messages = state.get("messages", [])
        reflection = state.get("reflection")
        retry_count = state.get("retry_count", 0)

        if not current_messages:
            return {
                "messages": [AIMessage(content="Tidak ada pesan untuk diproses.")],
                "retry_count": retry_count
            }        # Enhanced logic for detecting new user queries and context changes
        last_message = current_messages[-1] if current_messages else None
        is_new_user_query = (last_message and
                             hasattr(last_message, 'type') and
                             last_message.type == 'human')

        # Check for context change - compare current query with previous reflection context
        context_changed = False
        if is_new_user_query and reflection:
            current_query = last_message.content.lower()

            # Get previous queries from reflection guidance
            previous_context_hints = []
            if hasattr(reflection, 'critique') and reflection.critique:
                previous_context_hints.append(reflection.critique.lower())
            if hasattr(reflection, 'reasoning') and reflection.reasoning:
                previous_context_hints.append(reflection.reasoning.lower())

            # Check if current query has significantly different intent
            visualization_keywords = ['grafik', 'chart',
                                      'visualisasi', 'pie', 'bar', 'diagram']
            current_wants_viz = any(
                keyword in current_query for keyword in visualization_keywords)
            previous_suggested_viz = any(
                'visualization' in hint or 'grafik' in hint for hint in previous_context_hints)

            # Context changed if:
            # 1. Previous wanted visualization but current doesn't
            # 2. Current query is much shorter/simpler than previous complex requests
            # 3. Query focus changed (different cities, different data types)
            if previous_suggested_viz and not current_wants_viz:
                context_changed = True
                print(
                    "🔄 Context changed: Previous query wanted visualization, current doesn't")
            elif len(current_query.split()) <= 6 and any(len(hint.split()) > 15 for hint in previous_context_hints):
                context_changed = True
                print(
                    "🔄 Context changed: Current query much simpler than previous complex request")

        # Reset reflection if this is a new user query or context changed
        if is_new_user_query and (not reflection or context_changed):
            if reflection:
                print(
                    "🔄 New user query detected with context change - resetting reflection state")
            reflection = None
            retry_count = 0

        is_final_response = (reflection and
                             reflection.next_action == "FINISH" and
                             reflection.is_sufficient and
                             any(msg.type == 'tool' for msg in current_messages) and
                             not is_new_user_query)  # Don't generate final response for new user queries

        try:
            if is_final_response:
                # Generate final natural language response based on tool results
                print("🎯 Generating final response based on tool results...")

                final_response_prompt = """
Anda adalah ICONNET Assistant. Berdasarkan hasil tool yang telah dijalankan dalam percakapan ini, 
buatlah respons yang natural dan informatif untuk menjawab pertanyaan pengguna.

PANDUAN RESPONS FINAL:
1. Jawab pertanyaan pengguna berdasarkan data/hasil yang diperoleh dari tools
2. Berikan informasi yang akurat dan mudah dipahami
3. Jika ada data numerik, tampilkan dengan format yang rapi
4. Gunakan bahasa Indonesia yang natural dan profesional
5. JANGAN gunakan tools lagi - fokus hanya pada merangkum hasil yang sudah ada

Tugas Anda: Buat respons final yang menjawab pertanyaan pengguna berdasarkan hasil tool execution yang sudah dilakukan.
"""
                from langchain_core.messages import SystemMessage
                final_messages = [SystemMessage(
                    content=final_response_prompt)] + current_messages
                # Use LLM without tools for final response
                response = primary_llm.invoke(final_messages)

                return {
                    "messages": [response],
                    "retry_count": retry_count,
                    # Include the (possibly reset) reflection state
                    "reflection": reflection
                }

            else:
                # Regular tool execution flow
                # Smart guidance logic - only use reflection guidance if context hasn't changed
                guidance_prompt = ""
                current_query = last_message.content.lower() if last_message else ""

                # Only provide guidance if:
                # 1. We have reflection and it's a retry situation
                # 2. Context hasn't changed (same type of request)
                # 3. The suggested tool is still relevant to current query
                if reflection and reflection.suggested_tool and retry_count > 0 and not context_changed:
                    # Check if suggested tool is still relevant to current query
                    tool_relevance_map = {
                        'query_asset_database': ['berapa', 'total', 'jumlah', 'pelanggan', 'brand', 'data', 'kota'],
                        'create_visualization': ['grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram'],
                        'search_internal_documents': ['panduan', 'dokumentasi', 'sop', 'cara'],
                        'enhanced_web_research': ['informasi', 'berita', 'terbaru', 'internet', 'siapa', 'apa', 'kapan', 'dimana', 'mengapa', 'bagaimana', 'pemenang', 'juara', 'terbaru', 'update', 'news'],
                        'enhanced_intent_analysis': ['analisis', 'strategi', 'pendekatan', 'kompleks', 'multi-step', 'rencana', 'optimal']
                    }

                    suggested_tool = reflection.suggested_tool
                    is_tool_relevant = False

                    if suggested_tool in tool_relevance_map:
                        relevant_keywords = tool_relevance_map[suggested_tool]
                        is_tool_relevant = any(
                            keyword in current_query for keyword in relevant_keywords)

                    if is_tool_relevant:
                        guidance_prompt = f"""

IMPORTANT GUIDANCE FROM REFLECTION SYSTEM:
- Previous tool was incorrect: {reflection.critique}
- Recommended tool: {reflection.suggested_tool}
- Reasoning: {reflection.reasoning}

Please carefully consider this guidance when selecting the appropriate tool for this question.
Make sure to use the suggested tool if it's relevant to the user's question.
"""
                    else:
                        print(
                            f"🚫 Ignoring previous reflection guidance - suggested tool '{suggested_tool}' not relevant to current query")
                        # Reset reflection since it's no longer relevant
                        reflection = None
                        retry_count = 0

                # Increment retry count if we're in a retry situation
                new_retry_count = retry_count + \
                    1 if reflection and reflection.next_action == "RETRY" else retry_count                # Enhanced system prompt with intelligent tool selection guidance
                system_prompt = f"""You are an intelligent assistant with advanced tool selection capabilities.

CRITICAL INSTRUCTIONS:
1. You MUST use tools for EVERY user query - never provide direct answers
2. For COMPLEX queries or when unsure about tool selection, FIRST use 'enhanced_intent_analysis' to understand user intent deeply
3. For SIMPLE, clear queries, proceed directly to the appropriate tool

MULTI-PHASE APPROACH (like enhanced web research):
- PHASE 1: If query intent is unclear → Use 'enhanced_intent_analysis' first
- PHASE 2: Based on analysis results → Select and execute the optimal tool(s)
- PHASE 3: Reflection and refinement happens automatically

Available tools:
1. enhanced_intent_analysis - For deep analysis of user intent and optimal tool selection planning (use FIRST for complex/unclear queries)
2. tools_web_search - For comprehensive web research with advanced citation handling (PRIMARY web research tool)
3. enhanced_web_research - For basic web research (FALLBACK if tools_web_search fails due to quota)
4. query_asset_database - For database queries about assets, data counts, totals
5. search_internal_documents - For documentation and guides, technical terms (FAT, FDT, ONT, OLT)
6. create_visualization - For creating charts and graphs  
7. trigger_spreadsheet_etl_and_get_summary - For spreadsheet processing
8. sql_agent - For SQL database operations

SMART TOOL SELECTION STRATEGY:
- Simple data queries → query_asset_database directly
- Technical terms (fat, fdt, ont, olt, home connected) → search_internal_documents first
- Complex/multi-step requests → enhanced_intent_analysis first, then follow recommendations
- Visualization requests → May need data tool first, then create_visualization
- Internet research → tools_web_search (primary), enhanced_web_research (fallback)
- Documentation → search_internal_documents directly
- UNCLEAR/UNKNOWN queries → tools_web_search as reliable first choice, enhanced_web_research as backup

FALLBACK HIERARCHY:
1. Primary: Most specific tool for query type
2. Secondary: search_internal_documents for technical terms
3. Tertiary: tools_web_search for web research (with enhanced_web_research fallback if quota exceeded)

QUOTA AWARENESS: If tools_web_search returns quota exceeded messages, automatically suggest enhanced_web_research as alternative.

NEVER give direct LLM responses without using tools!

Current Query: "{current_query}"
Analysis: Determine if this is a simple direct query or needs sophisticated intent analysis first."""

                # Create messages with system prompt
                from langchain_core.messages import SystemMessage
                messages_with_system = [SystemMessage(
                    content=system_prompt)] + current_messages

                # Jika ada guidance, tambahkan ke context
                if guidance_prompt:
                    # Buat copy dari messages dan tambahkan guidance
                    messages_with_guidance = messages_with_system.copy()
                    # Ambil pesan user terakhir dan tambahkan guidance
                    for i in range(len(messages_with_guidance) - 1, -1, -1):
                        if hasattr(messages_with_guidance[i], 'type') and messages_with_guidance[i].type == 'human':
                            original_content = messages_with_guidance[i].content
                            messages_with_guidance[i].content = original_content + \
                                guidance_prompt
                            break

                    print(
                        f"🔄 Retrying with guidance for tool: {reflection.suggested_tool}")
                    response = primary_llm_with_tools.invoke(
                        messages_with_guidance)
                else:
                    response = primary_llm_with_tools.invoke(
                        messages_with_system)

                return {
                    "messages": [response],
                    "retry_count": new_retry_count,
                    # Include the (possibly reset) reflection state
                    "reflection": reflection
                }

        except Exception as e:
            print(f"Error in chatbot node during LLM invocation: {e}")
            error_response = AIMessage(
                content=f"Maaf, terjadi kesalahan saat saya mencoba memproses permintaan Anda dengan LLM: {str(e)}")
            return {
                "messages": [error_response],
                "retry_count": retry_count
            }

    # Build the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    # Tambahkan reflection node
    graph_builder.add_node("reflection_node", reflection_node)

    # Setup edges dengan reflection loop
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {
            "tools": "tools",
            "__end__": "__end__",
        },
    )

    # Setelah tools selesai, lakukan reflection
    graph_builder.add_edge("tools", "reflection_node")
    # Dari reflection, tentukan apakah retry atau finish
    graph_builder.add_conditional_edges(
        "reflection_node",
        should_retry_or_finish,
        {
            "chatbot": "chatbot",  # Retry atau Create final response
            "__end__": "__end__",   # Only untuk max retry atau error
        },
    )

    try:
        memory = MemorySaver()
        graph = graph_builder.compile(checkpointer=memory)
        return graph
    except Exception as e:
        return None
