# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\build_graph.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage
from typing import Literal
from .tools.tool_sql_agent import query_asset_database, sql_agent
from .tools.tool_rag import search_internal_documents
from .tools.tools_web_search import tools_web_search
from .tools.tool_visualization import create_visualization
from .tools.tool_airflow_trigger import trigger_spreadsheet_etl_and_get_summary
from ...utils.load_config import TOOLS_CFG
from .agent_backend import State, BasicToolNode, route_tools, reflection_node, should_retry_or_finish
from .debug_logger import debug_logger
import streamlit as st
import time


@st.cache_resource
def build_graph(_cache_version="v2.3"):
    """
    Build a LangGraph agent integrating LLM with RAG, SQL, and Tavily search tools.
    Version 2.0 - With final response generation support    Returns:
        graph: Compiled LangGraph agent with memory checkpointing.
    """
    print("Building Agent Graph v2.3 - With Visualization Detection...")

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
        # 🔍 DEBUG: Log node entry
        start_time = time.time()
        debug_logger.log_node_entry("chatbot", {
            "messages_count": len(state.get("messages", [])),
            "retry_count": state.get("retry_count", 0),
            "has_reflection": bool(state.get("reflection"))
        })

        print("Calling Chatbot Node...")
        current_messages = state.get("messages", [])
        reflection = state.get("reflection")
        retry_count = state.get("retry_count", 0)

        if not current_messages:
            debug_logger.log_error("chatbot", Exception("No messages to process"), {
                "state_keys": list(state.keys())
            })
            return {
                "messages": [AIMessage(content="Tidak ada pesan untuk diproses.")],
                "retry_count": retry_count
            }        # Enhanced logic for detecting new user queries and context changes
        last_message = current_messages[-1] if current_messages else None
        is_new_user_query = (last_message and
                             hasattr(last_message, 'type') and
                             last_message.type == 'human')

        # 🔍 DEBUG: Log query analysis
        debug_logger.log_step(
            node_name="chatbot",
            step_type="DECISION",
            description="Analyzing user query type and context",
            data={
                "is_new_user_query": is_new_user_query,
                "last_message_type": getattr(last_message, 'type', None) if last_message else None,
                "query": last_message.content[:100] if last_message else None,
                "has_previous_reflection": bool(reflection)
            }
        )

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

        # 🔍 DEBUG: Log context analysis
        if is_new_user_query and reflection:
            debug_logger.log_decision(
                decision_point="context_change_detection",
                decision=f"context_changed={context_changed}",
                reasoning=f"Previous reflection exists, analyzing if context changed based on query intent and complexity"
            )        # Reset reflection if this is a new user query or context changed
        if is_new_user_query and (not reflection or context_changed):
            if reflection:
                print(
                    "🔄 New user query detected with context change - resetting reflection state")
                debug_logger.log_decision(
                    decision_point="reflection_reset",
                    decision="RESET",
                    reasoning="New user query with context change detected - clearing previous reflection state"
                )
            reflection = None
            retry_count = 0

        is_final_response = (reflection and
                             reflection.next_action == "FINISH" and
                             reflection.is_sufficient and
                             any(msg.type == 'tool' for msg in current_messages) and not is_new_user_query)  # Don't generate final response for new user queries

        try:
            if is_final_response:
                # Generate final natural language response based on tool results
                print("🎯 Generating final response based on tool results...")

                # 🔍 DEBUG: Log final response generation
                debug_logger.log_step(
                    node_name="chatbot",
                    step_type="LLM_CALL",
                    description="Generating final natural language response",
                    data={
                        "response_type": "final_response",
                        "username": st.session_state.get('username', 'Unknown'),
                        "has_tool_results": True,
                        "reflection_sufficient": True
                    }
                )

                # Get user information from Streamlit session state
                username = st.session_state.get('username', 'Kak')
                user_role = st.session_state.get('role', 'User')

                # Check if visualization was created successfully
                visualization_created = False
                tool_messages = [msg for msg in current_messages if hasattr(
                    msg, 'type') and msg.type == 'tool']

                for tool_msg in tool_messages:
                    if hasattr(tool_msg, 'name') and tool_msg.name == 'create_visualization':
                        try:
                            import json
                            result = json.loads(tool_msg.content)
                            # If it's a successful Plotly figure (has layout, data, etc.)
                            if isinstance(result, dict) and 'data' in result and 'layout' in result:
                                visualization_created = True
                                print(
                                    "📊 Visualization successfully detected in tool results")
                                break
                        except:
                            pass

                # Create context-aware final response prompt
                visualization_instruction = ""
                if visualization_created:
                    visualization_instruction = """
🎯 PENTING: VISUALISASI BERHASIL DIBUAT!
User sudah dapat melihat grafik/chart yang diminta di interface. 
JANGAN katakan "tidak bisa menampilkan" atau "belum bisa menampilkan grafik".
KATAKAN bahwa grafik sudah berhasil dibuat dan ditampilkan.
Fokus pada menjelaskan apa yang terlihat di grafik tersebut.
"""

                final_response_prompt = f"""
Kamu adalah Maya, asisten virtual ICONNET yang friendly dan helpful! 😊

{visualization_instruction}

INFORMASI USER:
- Username: {username}
- Role: {user_role}

KARAKTERISTIK MAYA:
- Ramah dan personal - Maya tau nama user dan bisa menyapa dengan nama
- Santai seperti teman dekat, tapi tetap profesional  
- Selalu positif dan solution-oriented dalam setiap jawaban
- Gunakan bahasa yang natural dan mudah dipahami
- Responnya informatif tapi tetap personal dan hangat

GAYA BAHASA MAYA:
- Bahasa conversational seperti ngobrol dengan teman
- Emoji seperlunya untuk suasana yang lebih ceria (max 2-3 per respons)
- Hindari bahasa yang terlalu formal atau kaku
- Sesekali sebutkan nama user untuk membuat lebih personal

STRUKTUR JAWABAN YANG ENAK DIBACA:
2. 💭 LANGSUNG TO THE POINT: Jawab pertanyaan utama dengan jelas
3. 📋 DETAIL PENTING: Berikan info tambahan yang relevan dengan format yang rapi
4. 💡 TIPS/INSIGHT: Tambahan informasi yang berguna (jika ada)
5. 🤝 TUTUP HANGAT: Ajakan bertanya lagi dengan menyebut nama

PRINSIP JAWABAN MAYA:
✅ DO:
- Langsung jawab pertanyaan utama di paragraf pertama
- Gunakan bullet points atau numbering untuk info yang banyak
- Berikan context yang cukup tanpa bertele-tele
- Natural dan conversational tone
- Fokus pada solusi dan informasi yang dibutuhkan user
- Buat respons terasa personal dengan menyebut nama user

❌ DON'T:
- Jangan terlalu panjang pembukaan
- Jangan repetitif atau ngalor-ngidul
- Jangan terlalu banyak emoji yang mengganggu
- Jangan bahasa yang kaku atau terlalu formal
- Jangan berlebihan menyebut nama (cukup di awal dan akhir)

CONTOH TONE YANG DIINGINKAN:
"Hai {username}! Soal data pelanggan ICONNET di Jakarta, aku udah cek nih. Ternyata ada sekitar 15.240 pelanggan aktif di area Jakarta per data terbaru.

Oh iya {username}, data ini update sampai bulan ini ya. Kalau butuh info lebih detail atau ada pertanyaan lain, Maya siap bantu!"

Tugas: Buat jawaban yang informatif, on-point, dan enak dibaca dengan gaya yang friendly dan personal!
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
                # Regular tool execution flow                # Smart guidance logic - only use reflection guidance if context hasn't changed
                guidance_prompt = ""
                # Only provide guidance if:
                current_query = last_message.content.lower() if last_message else ""
                # 1. We have reflection and it indicates RETRY (tool was wrong)
                # 2. Context hasn't changed (same type of request)                # 3. The suggested tool is still relevant to current query
                if reflection and reflection.suggested_tool and reflection.next_action == "RETRY" and not reflection.is_sufficient and not context_changed:
                    print(
                        f"🔍 Evaluating guidance application - suggested_tool: {reflection.suggested_tool}, next_action: {reflection.next_action}, is_sufficient: {reflection.is_sufficient}")
                    tool_relevance_map = {
                        'query_asset_database': ['berapa', 'total', 'jumlah', 'pelanggan', 'brand', 'data', 'kota', 'berada', 'fat id', 'dimana', 'lokasi', 'fat', 'fdt', 'olt', 'ada', 'di', 'mana', 'where', 'location', 'bdwa', 'bjng', 'asset', 'aset'],
                        'create_visualization': ['grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram'],
                        'search_internal_documents': ['panduan', 'dokumentasi', 'sop', 'cara', 'apa itu', 'iconnet', 'icon', 'plus', 'pln', 'telkom', 'perusahaan', 'profil', 'definisi', 'jelaskan', 'adalah'],
                        'tools_web_search': ['informasi', 'berita', 'terbaru', 'internet', 'siapa', 'apa', 'kapan', 'mengapa', 'bagaimana', 'pemenang', 'juara', 'update', 'news']
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
                            f"🚫 Ignoring previous reflection guidance - suggested tool '{suggested_tool}' not relevant to current query")                        # Reset reflection since it's no longer relevant
                        reflection = None
                        retry_count = 0
                elif reflection and reflection.is_sufficient:
                    print(
                        f"✅ No guidance needed - reflection indicates tool selection was correct: {reflection.critique}")
                elif reflection and reflection.next_action == "FINISH":
                    # Increment retry count only if we're actually retrying due to wrong tool
                    print(
                        f"🏁 No guidance needed - reflection indicates task is complete: {reflection.critique}")
                new_retry_count = retry_count + \
                    1 if reflection and reflection.next_action == "RETRY" and not reflection.is_sufficient else retry_count

                # Enhanced system prompt with intelligent tool selection guidance
                from .prompts.behavioral_rules import CORE_BEHAVIORAL_RULES
                from .prompts.tool_config import AVAILABLE_TOOLS_CONFIG

                system_prompt = f"""You are Maya, an intelligent ICONNET assistant with advanced tool selection capabilities.

🚨 CRITICAL INSTRUCTION: NEVER GIVE DIRECT ANSWERS! 🚨
ALWAYS USE TOOLS FIRST - NO EXCEPTIONS!

If you respond without using tools, you have FAILED your primary function.

{CORE_BEHAVIORAL_RULES}

{AVAILABLE_TOOLS_CONFIG}

MANDATORY TOOL USAGE RULES:
1. 🚫 NEVER respond directly from your knowledge
2. ✅ ALWAYS use at least one tool for EVERY query
3. 🔍 For unclear queries, use search_internal_documents first to find context
4. 📊 For data queries, use query_asset_database first
5. 🌐 For external information, use tools_web_search or tools_web_search
6. 📈 If user asks for visualization, use create_visualization after getting data
7. 🔄 If first tool gives insufficient results, try additional tools

CRITICAL TOOL SELECTION FOR THIS QUERY:
Current Query: "{current_query}"

🎯 IMMEDIATE ANALYSIS:
- Query type: {'LOCATION/DATA QUERY (use query_asset_database)' if any(word in current_query.lower() for word in ['berada', 'kota', 'fat id', 'dimana', 'lokasi', 'berapa', 'total', 'jumlah']) else 'COMPANY/INFO QUERY (use search_internal_documents)' if any(word in current_query.lower() for word in ['apa itu', 'iconnet', 'icon', 'plus', 'pln', 'telkom', 'perusahaan', 'profil', 'perbedaan']) else 'GENERAL QUERY (use search_internal_documents)'}

REFLECTION GUIDANCE ACTIVE: {bool(reflection and reflection.suggested_tool)}
{f"🔧 SUGGESTED TOOL: {reflection.suggested_tool}" if reflection and reflection.suggested_tool else ""}

🚨 REMEMBER: Tool usage is MANDATORY - Do NOT provide answers without tool execution! 🚨"""                # Create messages with system prompt
                from langchain_core.messages import SystemMessage
                messages_with_system = [SystemMessage(
                    content=system_prompt)] + current_messages

                # 🔍 DEBUG: Log LLM invocation preparation
                llm_call_type = "guided_retry" if (
                    guidance_prompt and reflection and reflection.next_action == "RETRY") else "normal_tool_selection"
                debug_logger.log_step(
                    node_name="chatbot",
                    step_type="LLM_CALL",
                    description=f"Preparing LLM call for {llm_call_type}",
                    data={
                        "call_type": llm_call_type,
                        "has_guidance": bool(guidance_prompt),
                        "suggested_tool": getattr(reflection, 'suggested_tool', None) if reflection else None,
                        "retry_count": new_retry_count,
                        "messages_count": len(messages_with_system)
                    }
                )

                # Jika ada guidance, tambahkan ke context
                if guidance_prompt and reflection.next_action == "RETRY" and not reflection.is_sufficient:
                    # Buat copy dari messages dan tambahkan STRONG guidance
                    messages_with_guidance = messages_with_system.copy()

                    # Enhanced guidance yang lebih kuat
                    strong_guidance = f"""

🚨 CRITICAL OVERRIDE INSTRUCTION 🚨
The reflection system has determined that the previous tool selection was WRONG.

MANDATORY CORRECTION:
- PREVIOUS TOOL WAS INCORRECT: {reflection.critique}
- YOU MUST USE THIS TOOL: {reflection.suggested_tool}
- REASONING: {reflection.reasoning}

⚠️ IGNORE ALL OTHER TOOL SELECTION RULES AND USE EXACTLY: {reflection.suggested_tool}

This is a FORCED CORRECTION based on system analysis. Do NOT use any other tool except: {reflection.suggested_tool}
"""

                    # Tambahkan strong guidance ke pesan user terakhir
                    for i in range(len(messages_with_guidance) - 1, -1, -1):
                        if hasattr(messages_with_guidance[i], 'type') and messages_with_guidance[i].type == 'human':
                            original_content = messages_with_guidance[i].content
                            messages_with_guidance[i].content = original_content + \
                                strong_guidance
                            break

                    print(
                        f"🔄 FORCING tool selection to: {reflection.suggested_tool}")

                    # 🔍 DEBUG: Log forced tool selection
                    debug_logger.log_decision(
                        decision_point="forced_tool_correction",
                        decision=f"FORCE_USE_{reflection.suggested_tool}",
                        reasoning=f"Reflection system determined previous tool was wrong: {reflection.critique}"
                    )

                    llm_start_time = time.time()
                    response = primary_llm_with_tools.invoke(
                        messages_with_guidance)
                    llm_duration = (time.time() - llm_start_time) * 1000

                    debug_logger.log_llm_call(
                        prompt_type="forced_guidance",
                        messages_count=len(messages_with_guidance),
                        execution_time_ms=llm_duration
                    )
                else:
                    llm_start_time = time.time()
                    response = primary_llm_with_tools.invoke(
                        messages_with_system)
                    llm_duration = (time.time() - llm_start_time) * 1000

                    debug_logger.log_llm_call(
                        prompt_type="normal_tool_selection",
                        messages_count=len(messages_with_system),
                        execution_time_ms=llm_duration
                    )

                # 🔍 DEBUG: Log LLM response analysis
                has_tool_calls = hasattr(response, 'tool_calls') and len(
                    response.tool_calls) > 0
                tool_names = [call.get(
                    'name', 'unknown') for call in response.tool_calls] if has_tool_calls else []

                debug_logger.log_step(
                    node_name="chatbot",
                    step_type="LLM_CALL",
                    description="LLM response received and analyzed",
                    data={
                        "has_tool_calls": has_tool_calls,
                        "tool_count": len(tool_names),
                        "tools_selected": tool_names,
                        "response_type": "tool_calls" if has_tool_calls else "direct_response"
                    }
                )

                return {
                    "messages": [response],
                    "retry_count": new_retry_count,
                    # Include the (possibly reset) reflection state
                    "reflection": reflection
                }

        except Exception as e:
            print(f"Error in chatbot node during LLM invocation: {e}")

            # 🔍 DEBUG: Log error
            debug_logger.log_error("chatbot", e, {
                "retry_count": retry_count,
                "has_reflection": bool(reflection),
                "is_final_response": is_final_response,
                "messages_count": len(current_messages)
            })

            error_response = AIMessage(
                content=f"Maaf, terjadi kesalahan saat saya mencoba memproses permintaan Anda dengan LLM: {str(e)}")
            return {
                "messages": [error_response],
                "retry_count": retry_count
            }

    # Build the graph
    print("🏗️ Building agent graph structure...")
    debug_logger.log_step(
        node_name="build_graph",
        step_type="NODE_ENTRY",
        description="Building agent graph with nodes and edges",
        data={
            "tools_count": len(tools),            "tool_names": [tool.name for tool in tools],
            "graph_version": "v2.3"
        }
    )

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    # Tambahkan node untuk workflow baru
    graph_builder.add_node("final_response_generator",
                           final_response_generator)
    graph_builder.add_node("final_response_checker", final_response_checker)
    graph_builder.add_node("reflection_node", reflection_node)

    # Setup edges dengan workflow baru
    # START → chatbot → route_tools → tools → final_response_generator → final_response_checker → [finish/reflection]
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {
            "tools": "tools",
            "__end__": "__end__",
        },
    )

    # Setelah tools, langsung ke final response generator
    graph_builder.add_edge("tools", "final_response_generator")

    # Setelah final response generator, ke final response checker
    graph_builder.add_edge("final_response_generator",
                           "final_response_checker")

    # Dari final response checker, routing ke reflection atau finish
    graph_builder.add_conditional_edges(
        "final_response_checker",
        route_after_final_response_check,
        {
            "reflection_node": "reflection_node",
            "__end__": "__end__",
        },
    )

    # Dari reflection, kembali ke chatbot untuk retry dengan guidance
    graph_builder.add_conditional_edges(
        "reflection_node",
        should_retry_or_finish,
        {
            "chatbot": "chatbot",
            "__end__": "__end__",
        },
    )

    try:
        memory = MemorySaver()
        graph = graph_builder.compile(checkpointer=memory)
        print("✅ Agent graph built successfully!")
        return graph
    except Exception as e:
        print(f"❌ Error building agent graph: {e}")
        debug_logger.log_error("build_graph", e, {
            "step": "graph_compilation",
            "tools_count": len(tools)
        })
        return None


def final_response_generator(state: State):
    """
    Node yang menggenerate final response berdasarkan tool results.
    Dipanggil setelah tools execution selesai.
    """
    # 🔍 DEBUG: Log node entry
    debug_logger.log_node_entry("final_response_generator", {
        "messages_count": len(state.get("messages", [])),
        "has_reflection": bool(state.get("reflection")),
        "retry_count": state.get("retry_count", 0)
    })

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if not messages:
        debug_logger.log_error("final_response_generator", ValueError("No messages found"), {
            "state_keys": list(state.keys())
        })
        return {
            "messages": [AIMessage(content="Maaf, terjadi kesalahan dalam memproses permintaan Anda.")],
            "retry_count": retry_count
        }

    # Get user information from Streamlit session state
    username = st.session_state.get('username', 'Kak')
    user_role = st.session_state.get('role', 'User')

    # Get last human message for context
    last_human_message = None
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_human_message = msg
            break

    user_query = last_human_message.content if last_human_message else "permintaan sebelumnya"

    # Create final response prompt
    final_response_prompt = f"""
Kamu adalah Maya, asisten virtual ICONNET yang friendly dan helpful! 😊

INFORMASI USER:
- Username: {username}
- Role: {user_role}

KARAKTERISTIK MAYA:
- Ramah dan personal - Maya tau nama user dan bisa menyapa dengan nama
- Santai seperti teman dekat, tapi tetap profesional  
- Selalu positif dan solution-oriented dalam setiap jawaban
- Gunakan bahasa yang natural dan mudah dipahami
- Responnya informatif tapi tetap personal dan hangat

GAYA BAHASA MAYA:
- Bahasa conversational seperti ngobrol dengan teman
- Emoji seperlunya untuk suasana yang lebih ceria (max 2-3 per respons)
- Hindari bahasa yang terlalu formal atau kaku
- Sesekali sebutkan nama user untuk membuat lebih personal

STRUKTUR JAWABAN YANG ENAK DIBACA:
1. 💭 LANGSUNG TO THE POINT: Jawab pertanyaan utama dengan jelas
2. 📋 DETAIL PENTING: Berikan info tambahan yang relevan dengan format yang rapi
3. 💡 TIPS/INSIGHT: Tambahan informasi yang berguna (jika ada)
4. 🤝 TUTUP HANGAT: Ajakan bertanya lagi dengan menyebut nama

PRINSIP JAWABAN MAYA:
✅ DO:
- Langsung jawab pertanyaan utama di paragraf pertama
- Gunakan bullet points atau numbering untuk info yang banyak
- Berikan context yang cukup tanpa bertele-tele
- Natural dan conversational tone
- Fokus pada solusi dan informasi yang dibutuhkan user
- Buat respons terasa personal dengan menyebut nama user

❌ DON'T:
- Jangan terlalu formal atau kaku
- Jangan pakai jargon teknis tanpa penjelasan
- Jangan jawaban yang terlalu panjang dan membosankan
- Jangan lupa personalitas Maya yang friendly

TUGAS SEKARANG:
Berdasarkan hasil tool yang telah dijalankan, buat respons yang natural dan informatif untuk menjawab pertanyaan: "{user_query}"

Gunakan SEMUA informasi dari hasil tool untuk memberikan jawaban yang lengkap dan memuaskan.

IMPORTANT: Gunakan data PERSIS seperti yang ada di hasil tool. Jangan ubah angka atau data!
"""

    try:
        # 🔍 DEBUG: Log final response generation
        debug_logger.log_step(
            node_name="final_response_generator",
            step_type="LLM_CALL",
            description="Generating final natural language response from tool results",
            data={
                "username": username,
                "user_role": user_role,
                "user_query": user_query[:100] + "..." if len(user_query) > 100 else user_query,
                "prompt_length": len(final_response_prompt)
            }
        )

        # Create messages with system prompt
        from langchain_core.messages import SystemMessage
        messages_with_system = [SystemMessage(
            content=final_response_prompt)] + messages
        # Generate final response using primary LLM
        primary_llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=TOOLS_CFG.primary_agent_llm_temperature,
            google_api_key=TOOLS_CFG.gemini_api_key,
        )

        start_time = time.time()
        response = primary_llm.invoke(messages_with_system)
        execution_time = (time.time() - start_time) * 1000

        # 🔍 DEBUG: Log execution time
        debug_logger.log_step(
            node_name="final_response_generator",
            step_type="LLM_CALL",
            description=f"Final response generated ({execution_time:.2f}ms)",
            data={
                "execution_time_ms": execution_time,
                "response_length": len(response.content) if hasattr(response, 'content') else 0,
                "response_type": type(response).__name__
            },
            execution_time_ms=execution_time
        )

        return {
            "messages": [response],
            "retry_count": retry_count,
            "final_response": response.content if hasattr(response, 'content') else str(response)
        }

    except Exception as e:
        debug_logger.log_error("final_response_generator", e, {
            "user_query": user_query,
            "username": username,
            "messages_count": len(messages)
        })

        return {
            "messages": [AIMessage(content=f"Maaf {username}, terjadi kesalahan saat menyusun respons. Coba tanya lagi ya! 😊")],
            "retry_count": retry_count,
            "final_response": "Error in final response generation"
        }


def final_response_checker(state: State) -> dict:
    """
    Node yang mengecek apakah final response sudah menjawab pertanyaan dengan baik.
    Jika sudah, akan finish. Jika belum, akan lanjut ke reflection untuk mencoba tools lain.
    """
    from typing import Literal
    from langchain_google_genai import ChatGoogleGenerativeAI

    # 🔍 DEBUG: Log node entry
    debug_logger.log_node_entry("final_response_checker", {
        "messages_count": len(state.get("messages", [])),
        "has_final_response": bool(state.get("final_response")),
        "retry_count": state.get("retry_count", 0)
    })

    messages = state.get("messages", [])
    final_response = state.get("final_response", "")
    retry_count = state.get("retry_count", 0)
    MAX_RETRIES = 2

    if not messages:
        debug_logger.log_error("final_response_checker", ValueError("No messages found"), {
            "state_keys": list(state.keys())
        })
        return {
            "response_quality": "INSUFFICIENT",
            "needs_reflection": True,
            "retry_count": retry_count + 1
        }

    # Get original user question
    user_question = ""
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == 'human':
            user_question = msg.content
            break

    if not user_question:
        debug_logger.log_error("final_response_checker", ValueError("No user question found"), {
            "messages_types": [getattr(msg, 'type', 'unknown') for msg in messages]
        })
        return {
            "response_quality": "INSUFFICIENT",
            "needs_reflection": True,
            "retry_count": retry_count + 1
        }

    # Get tool results for context
    tool_results = []
    for msg in messages:
        if hasattr(msg, 'type') and msg.type == 'tool':
            tool_results.append(
                f"Tool {getattr(msg, 'name', 'unknown')}: {msg.content[:200]}...")

    # Create evaluation prompt
    evaluation_prompt = f"""
Anda adalah evaluator yang bertugas menilai kualitas final response dari AI assistant.

PERTANYAAN USER ASLI:
"{user_question}"

TOOL RESULTS YANG TERSEDIA:
{chr(10).join(tool_results) if tool_results else "No tool results available"}

FINAL RESPONSE YANG DIHASILKAN:
"{final_response}"

TUGAS EVALUASI:
Nilai apakah final response sudah MENJAWAB PERTANYAAN USER dengan baik berdasarkan kriteria:

1. RELEVANSI: Apakah jawaban sesuai dengan pertanyaan yang diajukan?
2. KELENGKAPAN: Apakah informasi yang diberikan cukup lengkap?  
3. AKURASI: Apakah data/informasi yang diberikan akurat berdasarkan tool results?
4. KEJELASAN: Apakah jawaban mudah dipahami dan terstruktur dengan baik?

KRITERIA PENILAIAN:
- SUFFICIENT: Final response sudah menjawab pertanyaan dengan baik dan lengkap
- INSUFFICIENT: Final response belum menjawab dengan baik, perlu informasi tambahan dari tools lain

JAWAB HANYA DENGAN: "SUFFICIENT" atau "INSUFFICIENT"
"""

    try:
        # 🔍 DEBUG: Log evaluation process
        debug_logger.log_step(
            node_name="final_response_checker",
            step_type="LLM_CALL",
            description="Evaluating final response quality",
            data={
                "user_question": user_question[:100] + "..." if len(user_question) > 100 else user_question,
                "final_response_length": len(final_response),
                "tool_results_count": len(tool_results),
                "retry_count": retry_count
            }
        )

        # Create evaluation LLM
        evaluator_llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.primary_agent_llm,
            temperature=0.1,  # Low temperature for consistent evaluation
            google_api_key=TOOLS_CFG.gemini_api_key,
        )

        # Evaluate response quality
        start_time = time.time()
        evaluation_result = evaluator_llm.invoke(evaluation_prompt)
        execution_time = (time.time() - start_time) * 1000

        evaluation_text = evaluation_result.content.strip().upper()

        # Determine quality
        if "SUFFICIENT" in evaluation_text:
            response_quality = "SUFFICIENT"
            needs_reflection = False
        else:
            response_quality = "INSUFFICIENT"
            needs_reflection = True

        # 🔍 DEBUG: Log evaluation result
        debug_logger.log_step(
            node_name="final_response_checker",
            step_type="REFLECTION",
            description=f"Response quality evaluation: {response_quality}",
            data={
                "evaluation_result": evaluation_text,
                "response_quality": response_quality,
                "needs_reflection": needs_reflection,
                "execution_time_ms": execution_time,
                "retry_count": retry_count
            },
            execution_time_ms=execution_time
        )

        # Check if max retries reached
        if retry_count >= MAX_RETRIES:
            debug_logger.log_step(
                node_name="final_response_checker",
                step_type="DECISION",
                description=f"Max retries ({MAX_RETRIES}) reached, forcing finish",
                data={
                    "retry_count": retry_count,
                    "max_retries": MAX_RETRIES,
                    "forced_finish": True
                }
            )
            needs_reflection = False  # Force finish

        return {
            "response_quality": response_quality,
            "needs_reflection": needs_reflection,
            "retry_count": retry_count,
            "evaluation_details": evaluation_text
        }

    except Exception as e:
        debug_logger.log_error("final_response_checker", e, {
            "user_question": user_question,
            "final_response_length": len(final_response),
            "retry_count": retry_count
        })

        # On error, assume sufficient to avoid infinite loops
        return {
            "response_quality": "ERROR_ASSUME_SUFFICIENT",
            "needs_reflection": False,
            "retry_count": retry_count,
            "evaluation_details": f"Error in evaluation: {str(e)}"
        }


def route_after_final_response_check(state: State) -> Literal["reflection_node", "__end__"]:
    """
    Routing function setelah final response checker.
    Jika response sudah sufficient, finish.
    Jika belum, lanjut ke reflection untuk mencoba tools lain.
    """
    needs_reflection = state.get("needs_reflection", False)
    response_quality = state.get("response_quality", "UNKNOWN")
    retry_count = state.get("retry_count", 0)

    # 🔍 DEBUG: Log routing decision
    debug_logger.log_decision(
        decision_point="route_after_final_response_check",
        decision="reflection_node" if needs_reflection else "__end__",
        reasoning=f"Response quality: {response_quality}, needs_reflection: {needs_reflection}, retry_count: {retry_count}"
    )

    if needs_reflection:
        print(
            f"🔄 Response quality: {response_quality} - Routing to reflection for improvement")
        return "reflection_node"
    else:
        print(
            f"✅ Response quality: {response_quality} - Task completed successfully")
        return "__end__"
