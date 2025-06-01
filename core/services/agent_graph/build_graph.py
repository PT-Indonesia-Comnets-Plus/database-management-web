from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from .tool_sql_agent import query_asset_database, sql_agent
from .tool_rag import search_internal_documents
from .tool_tavily_search import load_tavily_search_tool
from .tool_visualization import create_visualization
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
    print("🏗️ Building Agent Graph...")

    try:
        # Determine Gemini model name and temperature from TOOLS_CFG or use defaults
        gemini_model_name = "gemini-1.5-flash"
        if hasattr(TOOLS_CFG, 'primary_agent_llm') and TOOLS_CFG.primary_agent_llm and "gemini" in str(TOOLS_CFG.primary_agent_llm).lower():
            gemini_model_name = TOOLS_CFG.primary_agent_llm

        gemini_temperature = 0.7  # Default temperature for general tasks
        if hasattr(TOOLS_CFG, 'primary_agent_llm_temperature'):
            try:
                gemini_temperature = float(
                    TOOLS_CFG.primary_agent_llm_temperature)
            except ValueError:
                print(
                    f"Warning: Could not parse primary_agent_llm_temperature '{TOOLS_CFG.primary_agent_llm_temperature}' as float. Using default {gemini_temperature}.")

        primary_llm = ChatGoogleGenerativeAI(
            model=gemini_model_name,
            temperature=gemini_temperature,
            convert_system_message_to_human=True
        )
        print(
            f"Primary LLM (Gemini) initialized: model={gemini_model_name}, temperature={gemini_temperature}")

    except Exception as e:
        print(f"❌ Error initializing Gemini LLM in build_graph: {e}")
        st.error(f"❌ Gagal menginisialisasi LLM utama (Gemini): {e}")
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
        ]
        primary_llm_with_tools = primary_llm.bind_tools(tools)
        print(f"🛠️ Tools bound to LLM: {[tool.name for tool in tools]}")
    except Exception as e:
        st.error(f"❌ Failed to load or bind tools: {e}")
        print(f"❌ Failed to load or bind tools: {e}")
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
        print("💬 Calling Chatbot Node...")
        current_messages = state.get("messages", [])
        if not current_messages:  # Seharusnya tidak terjadi jika START ke chatbot
            return {"messages": [AIMessage(content="Tidak ada pesan untuk diproses.")]}
        try:
            response = primary_llm_with_tools.invoke(current_messages)
            return {"messages": [response]}
        except Exception as e:
            print(f"❌ Error in chatbot node during LLM invocation: {e}")
            error_response = AIMessage(
                content=f"Maaf, terjadi kesalahan saat saya mencoba memproses permintaan Anda dengan LLM: {str(e)}")
            # Mengembalikan pesan error sebagai AIMessage baru
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
