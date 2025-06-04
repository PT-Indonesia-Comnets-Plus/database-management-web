# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\build_graph.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from .tool_sql_agent import query_asset_database, sql_agent
from .tool_rag import search_internal_documents
from .tool_tavily_search import load_tavily_search_tool
from .tool_visualization import create_visualization
from .tool_airflow_trigger import trigger_spreadsheet_etl_and_get_summary
from ...utils.load_config import TOOLS_CFG
from .agent_backend import State, BasicToolNode, route_tools
import streamlit as st


@st.cache_resource
def build_graph():
    """
    Build a LangGraph agent integrating LLM with RAG, SQL, and Tavily search tools.

    Returns:
        graph: Compiled LangGraph agent with memory checkpointing.
    """
    print("Building Agent Graph...")

    try:
        primary_llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
        )
    except Exception as e:
        return None

    try:
        tavily_search_tool = load_tavily_search_tool(
            TOOLS_CFG.tavily_search_max_results)

        tools = [
            search_internal_documents,
            query_asset_database,
            sql_agent,
            tavily_search_tool,
            create_visualization,
            trigger_spreadsheet_etl_and_get_summary,
        ]
        primary_llm_with_tools = primary_llm.bind_tools(tools)
        print(f"Tools bound to LLM: {[tool.name for tool in tools]}")
    except Exception as e:
        st.error(f"Failed to load or bind tools: {e}")
        print(f"Failed to load or bind tools: {e}")
        return None

    graph_builder = StateGraph(State)

    def chatbot(state: State):
        """
        Node that runs the primary LLM agent with bound tools.

        Args:
            state (State): Current state containing conversation messages.

        Returns:
            dict: Updated messages after LLM invocation.
        """
        print("Calling Chatbot Node...")
        current_messages = state.get("messages", [])
        if not current_messages:
            return {"messages": [AIMessage(content="Tidak ada pesan untuk diproses.")]}
        try:
            response = primary_llm_with_tools.invoke(current_messages)
            return {"messages": [response]}
        except Exception as e:
            print(f"Error in chatbot node during LLM invocation: {e}")
            error_response = AIMessage(
                content=f"Maaf, terjadi kesalahan saat saya mencoba memproses permintaan Anda dengan LLM: {str(e)}")
            return {"messages": [error_response]}

    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {
            "tools": "tools",
            "__end__": "__end__",
        },
    )
    graph_builder.add_edge("tools", "chatbot")

    try:
        memory = MemorySaver()
        graph = graph_builder.compile(checkpointer=memory)
        return graph
    except Exception as e:
        return None
