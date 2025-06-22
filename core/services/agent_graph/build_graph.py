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
                    1 if reflection and reflection.next_action == "RETRY" and not reflection.is_sufficient else retry_count                # Enhanced system prompt with intelligent tool selection guidance
                # Define behavioral rules and tool config inline
                CORE_BEHAVIORAL_RULES = """
KARAKTERISTIK MAYA (ICONNET Assistant):
- 🎯 Selalu menggunakan tools terlebih dahulu sebelum memberikan jawaban
- 🔍 Tidak pernah memberikan jawaban langsung dari pengetahuan internal
- 📊 Prioritaskan akurasi data dengan menggunakan tools yang tepat
- 🌟 Responsif dan membantu dengan bahasa yang ramah dan profesional
"""

                AVAILABLE_TOOLS_CONFIG = """
TOOLS YANG TERSEDIA:
1. 🗂️ search_internal_documents: Cari informasi dalam dokumentasi internal ICONNET
2. 📊 query_asset_database: Query database aset untuk data pelanggan, lokasi, FAT ID
3. 🤖 sql_agent: Analisis data kompleks dengan SQL
4. 🌐 tools_web_search: Cari informasi terbaru di internet
5. 📈 create_visualization: Buat grafik dan visualisasi data
6. 🔄 trigger_spreadsheet_etl: Proses data dari spreadsheet
"""                # Check if there are pending tools from multi-tool router
                pending_tools = state.get("pending_tools", [])
                tools_used_already = []
                for msg in current_messages:
                    if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name'):
                        tools_used_already.append(msg.name)

                # Add specific tool guidance for multi-tool scenarios
                multi_tool_guidance = state.get("multi_tool_guidance", "")

                # If no multi_tool_guidance from state, check local pending tools
                if not multi_tool_guidance and pending_tools:
                    if 'create_visualization' in pending_tools and any(tool in tools_used_already for tool in ['query_asset_database', 'sql_agent']):
                        multi_tool_guidance = """

🎯 MULTI-TOOL CONTINUATION:
Previous tools have been executed successfully. Now you MUST use create_visualization tool to generate the requested chart/graph.

MANDATORY: Use create_visualization tool to create the visualization based on the data from previous tool results.
"""

                system_prompt = f"""You are Maya, an intelligent ICONNET assistant with advanced tool selection capabilities.

🚨 CRITICAL INSTRUCTION: NEVER GIVE DIRECT ANSWERS! 🚨
ALWAYS USE TOOLS FIRST - NO EXCEPTIONS!

If you respond without using tools, you have FAILED your primary function.

{CORE_BEHAVIORAL_RULES}

{AVAILABLE_TOOLS_CONFIG}

{multi_tool_guidance}

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
- Query type: {'LOCATION/DATA QUERY (use query_asset_database)' if any(word in current_query.lower() for word in ['berada', 'kota', 'fat id', 'dimana', 'lokasi', 'berapa pelanggan', 'total pelanggan', 'jumlah pelanggan', 'data pelanggan', 'berapa hc', 'hc per', 'headcount']) else 'COMPANY/INFO QUERY (use search_internal_documents)' if any(word in current_query.lower() for word in ['apa itu', 'iconnet', 'icon', 'plus', 'pln', 'telkom', 'perusahaan', 'profil', 'perbedaan', 'tahun', 'berdiri', 'sejarah', 'didirikan', 'kapan']) else 'GENERAL QUERY (use search_internal_documents)'}

MULTI-TOOL DETECTION:
- Needs data query: {'YES' if any(word in current_query.lower() for word in ['berapa', 'data', 'jumlah', 'total', 'hc per', 'headcount']) else 'NO'}
- Needs visualization: {'YES' if any(word in current_query.lower() for word in ['grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram', 'buatkan grafik', 'buat grafik']) else 'NO'}

🚨 MULTI-TOOL STRATEGY:
If query needs BOTH data AND visualization:
1. FIRST use query_asset_database OR sql_agent to get data
2. THEN use create_visualization to make charts
3. Do NOT generate final response until ALL required tools are used!

TOOLS ALREADY USED: {tools_used_already}
PENDING TOOLS: {pending_tools}

REFLECTION GUIDANCE ACTIVE: {bool(reflection and reflection.suggested_tool)}
{f"🔧 SUGGESTED TOOL: {reflection.suggested_tool}" if reflection and reflection.suggested_tool else ""}

🚨 REMEMBER: Tool usage is MANDATORY - Do NOT provide answers without tool execution! 🚨"""  # Create messages with system prompt
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
                )                # Jika ada guidance, tambahkan ke system prompt bukan ke user message
                if guidance_prompt and reflection.next_action == "RETRY" and not reflection.is_sufficient:
                    # Enhanced guidance yang lebih kuat - tambahkan ke SYSTEM PROMPT
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

                    # Tambahkan strong guidance ke SYSTEM PROMPT, bukan ke user message
                    enhanced_system_prompt = system_prompt + strong_guidance

                    # Buat messages dengan enhanced system prompt
                    from langchain_core.messages import SystemMessage
                    messages_with_guidance = [SystemMessage(
                        content=enhanced_system_prompt)] + current_messages

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

    def final_response_generator(state: State):
        """
        📝 Final Response Generator Node
        Generates the final natural language response based on tool results.
        """
        debug_logger.log_node_entry("final_response_generator", {
            "messages_count": len(state.get("messages", [])),
            "has_tool_results": any(msg.type == 'tool' for msg in state.get("messages", []) if hasattr(msg, 'type'))
        })

        current_messages = state.get("messages", [])
        retry_count = state.get("retry_count", 0)

        try:
            # Get the user query
            user_query = ""
            for msg in reversed(current_messages):
                if hasattr(msg, 'type') and msg.type == 'human':
                    user_query = msg.content
                    break

            # Check what tools were used
            tools_used = []
            tool_results = []
            for msg in current_messages:
                if hasattr(msg, 'type') and msg.type == 'tool':
                    if hasattr(msg, 'name'):
                        tools_used.append(msg.name)
                    if hasattr(msg, 'content'):
                        tool_results.append(msg.content)

            print(f"📝 Final Response Generator:")
            print(f"   Query: {user_query[:100]}...")
            print(f"   Tools Used: {tools_used}")
            # Check if visualization was created
            print(f"   Tool Results Available: {len(tool_results)}")
            has_visualization = 'create_visualization' in tools_used
            visualization_success = False

            if has_visualization:
                # Check if visualization was successful by looking at tool results
                for msg in current_messages:
                    if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name') and msg.name == 'create_visualization':
                        try:
                            import json
                            result = json.loads(msg.content)
                            if isinstance(result, dict) and 'data' in result and 'layout' in result:
                                visualization_success = True
                                break
                        except:
                            pass

            # Generate final response prompt
            if has_visualization and visualization_success:
                final_response_prompt = """Anda adalah ICONNET Assistant yang ramah dan informatif.

🎯 PENTING: VISUALISASI BERHASIL DIBUAT!
User dapat melihat grafik/chart yang diminta di interface. 
JANGAN katakan "tidak bisa menampilkan" atau "maaf tidak dapat menampilkan grafik".
KATAKAN bahwa grafik sudah berhasil dibuat dan ditampilkan.

Berdasarkan hasil tools yang telah dijalankan, buatlah response yang:
1. ✅ KONFIRMASI bahwa grafik sudah berhasil dibuat dan ditampilkan
2. 📊 Jelaskan apa yang terlihat di grafik berdasarkan data
3. 📍 Berikan informasi spesifik tentang data HC per kota
4. 💡 Tambahkan insight atau analisis dari data
5. 🤝 Gunakan bahasa yang ramah dan mudah dipahami

HINDARI kata-kata: "tidak bisa menampilkan", "maaf tidak dapat", "keterbatasan sistem"
GUNAKAN kata-kata: "grafik sudah dibuat", "sudah ditampilkan", "bisa dilihat di atas"

Pastikan response Anda mengkonfirmasi bahwa visualisasi berhasil dan fokus pada penjelasan data."""
            else:
                final_response_prompt = """Anda adalah ICONNET Assistant yang ramah dan informatif.

Berdasarkan hasil tools yang telah dijalankan, buatlah response yang:
1. 🎯 Menjawab pertanyaan user secara lengkap dan akurat
2. 🌟 Menggunakan emoji untuk membuat response lebih menarik  
3. 📍 Berikan informasi yang spesifik dan detail
4. 💡 Tambahkan saran atau informasi tambahan yang relevan
5. 🤝 Gunakan bahasa yang ramah dan mudah dipahami

Pastikan response Anda berdasarkan data faktual dari tools dan memberikan value yang tinggi untuk user."""

            final_messages = [
                AIMessage(content=final_response_prompt)] + current_messages

            # Use primary LLM without tools for final response generation
            response = primary_llm.invoke(final_messages)

            print(
                f"✅ Final response generated: {len(response.content)} characters")

            debug_logger.log_step(
                node_name="final_response_generator",
                step_type="RESPONSE_GENERATED",
                description="Final response generated successfully",
                data={
                    "response_length": len(response.content),
                    "tools_used": tools_used,
                    "user_query_length": len(user_query)
                }
            )

            return {
                "messages": [response],
                "retry_count": retry_count,
                "final_response": response.content,
                "user_query": user_query,
                "tools_used": tools_used
            }

        except Exception as e:
            print(f"❌ Error in final response generator: {e}")
            debug_logger.log_error("final_response_generator", e)

            error_response = AIMessage(
                content="Maaf, terjadi kesalahan saat menghasilkan response akhir.")
            return {
                "messages": [error_response],
                "retry_count": retry_count,                "final_response": error_response.content,
                "user_query": user_query if 'user_query' in locals() else "",
                "tools_used": tools_used if 'tools_used' in locals() else []
            }

    def final_response_checker(state: State):
        """
        🔍 Final Response Checker Node
        Evaluates the quality of the final response and determines next action.
        """
        debug_logger.log_node_entry("final_response_checker", {
            "has_final_response": bool(state.get("final_response")),
            "retry_count": state.get("retry_count", 0)
        })

        final_response = state.get("final_response", "")
        user_query = state.get("user_query", "")
        tools_used = state.get("tools_used", [])
        retry_count = state.get("retry_count", 0)

        print(f"🔍 Final Response Quality Check:")
        print(f"   Response length: {len(final_response)} characters")
        print(f"   Query: {user_query[:100]}...")
        print(f"   Tools used: {tools_used}")
        print(f"   🔧 DEBUG - State keys: {list(state.keys())}")
        print(
            f"   🔧 DEBUG - final_response from state: {final_response[:100] if final_response else 'EMPTY'}...")
        print(
            f"   🔧 DEBUG - user_query from state: {user_query[:50] if user_query else 'EMPTY'}...")
        print(f"   🔧 DEBUG - tools_used from state: {tools_used}")

        # Simple quality evaluation
        is_sufficient = True
        suggested_tool = ""

        # Check for insufficient patterns
        insufficient_patterns = [
            "maaf, saya tidak dapat",
            "informasi tidak tersedia",
            "tidak ditemukan",
            "tidak ada data",
            "mohon maaf"
        ]

        has_insufficient_response = any(
            pattern in final_response.lower() for pattern in insufficient_patterns)
        # Check if response is too short
        is_too_short = len(final_response.split()) < 10

        # For company info queries, ensure we used the right tool
        if any(keyword in user_query.lower() for keyword in ['tahun', 'berdiri', 'didirikan', 'kapan', 'iconnet', 'icon', 'plus', 'perusahaan', 'profil', 'sejarah']):
            if 'search_internal_documents' not in tools_used:
                is_sufficient = False
                suggested_tool = 'search_internal_documents'
                print(
                    f"❌ Company info query should use search_internal_documents, used: {tools_used}")

        # For FAT ID queries, ensure we have proper location information
        elif any(keyword in user_query.lower() for keyword in ['fat', 'lokasi', 'dimana', 'kota', 'kecamatan', 'kelurahan']):
            has_location_info = any(info in final_response.lower() for info in [
                                    'kota', 'kecamatan', 'kelurahan', 'alamat', 'koordinat'])
            if not has_location_info and 'query_asset_database' not in tools_used:
                is_sufficient = False
                suggested_tool = 'query_asset_database'
        if has_insufficient_response or is_too_short:
            is_sufficient = False
            # Only override if not already set by tool check above
            if not suggested_tool:
                # Priority check: company info should use search_internal_documents
                if any(keyword in user_query.lower() for keyword in ['tahun', 'berdiri', 'didirikan', 'kapan', 'iconnet', 'icon', 'plus', 'perusahaan', 'profil', 'sejarah']):
                    suggested_tool = 'search_internal_documents'
                elif any(keyword in user_query.lower() for keyword in ['fat', 'lokasi', 'data', 'berapa']):
                    suggested_tool = 'query_asset_database'
                else:
                    suggested_tool = 'search_internal_documents'

        debug_logger.log_step(
            node_name="final_response_checker",
            step_type="QUALITY_CHECK",
            description="Response quality evaluation completed",
            data={
                "is_sufficient": is_sufficient,
                "has_insufficient_response": has_insufficient_response,
                "is_too_short": is_too_short,
                "suggested_tool": suggested_tool
            }
        )

        if is_sufficient:
            print(f"✅ Response quality: SUFFICIENT")
            return {
                **state,
                "reflection": None,
                "quality_check_result": "SUFFICIENT"
            }
        else:
            print(f"❌ Response quality: INSUFFICIENT")
            print(f"💡 Suggested improvement: Use {suggested_tool}")

            # Import Reflection here to avoid circular imports
            from .agent_backend import Reflection

            reflection = Reflection(
                critique=f"Response insufficient for query: {user_query[:50]}...",
                suggested_tool=suggested_tool,
                reasoning=f"Quality check failed. Response was insufficient or wrong tools used.",
                next_action="RETRY",
                is_sufficient=False
            )

            return {**state,
                    "reflection": reflection,
                    "quality_check_result": "INSUFFICIENT",
                    "retry_count": retry_count + 1
                    }

    def multi_tool_router(state: State):
        """
        🔄 Multi-Tool Router Node
        Determines if more tools are needed before generating final response.
        This is a NODE that updates state and returns state dict, not a routing function.
        """
        debug_logger.log_node_entry("multi_tool_router", {
            "messages_count": len(state.get("messages", [])),
            "retry_count": state.get("retry_count", 0)
        })

        messages = state.get("messages", [])

        # Get the original user query
        user_query = ""
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'human':
                user_query = msg.content.lower()
                break

        # Check what tools have been used
        tools_used = []
        for msg in messages:
            if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name'):
                tools_used.append(msg.name)

        print(f"🔄 Multi-Tool Router:")
        print(f"   Query: {user_query[:100]}...")
        print(f"   Tools used: {tools_used}")

        # Detect if user wants both data and visualization
        needs_data = any(word in user_query for word in [
            'berapa', 'data', 'jumlah', 'total', 'hc per', 'headcount'
        ])
        needs_visualization = any(word in user_query for word in [
            'grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram',
            'buatkan grafik', 'buat grafik', 'batang'
        ])

        # Check if data query tools have been used
        data_tools_used = any(tool in tools_used for tool in [
            'query_asset_database', 'sql_agent'
        ])

        # Check if visualization tool has been used
        viz_tool_used = 'create_visualization' in tools_used

        print(
            f"   Needs data: {needs_data}, Data tools used: {data_tools_used}")
        print(
            f"   Needs viz: {needs_visualization}, Viz tool used: {viz_tool_used}")        # Decision logic
        if needs_data and needs_visualization:
            if data_tools_used and not viz_tool_used:
                print("   ➡️ Need visualization tool - routing back to chatbot")
                debug_logger.log_decision(
                    decision_point="multi_tool_router",
                    decision="NEED_VISUALIZATION",
                    reasoning="Data retrieved, now need visualization tool"
                )

                print(
                    f"   🔧 DEBUG: Setting next_route=CHATBOT, pending_tools=[create_visualization]")
                return {
                    **state,
                    "next_route": "CHATBOT",
                    "pending_tools": ["create_visualization"],
                    "multi_tool_guidance": f"""
🎯 CRITICAL MULTI-TOOL INSTRUCTION:
User requested: "{user_query[:100]}..."

CURRENT STATUS:
✅ Data retrieved with: {data_tools_used and tools_used}
❌ MISSING: Visualization tool

MANDATORY NEXT ACTION:
- You MUST use create_visualization tool
- Use the data from previous tool results
- Create the requested chart/graph type (grafik batang/bar chart)
- DO NOT provide final response until visualization is complete

FORCE USE: create_visualization tool with the retrieved data."""
                }
            elif not data_tools_used:
                print("   ➡️ Need data tool first - routing back to chatbot")
                print(
                    f"   🔧 DEBUG: Setting next_route=CHATBOT, pending_tools=[query_asset_database, create_visualization]")
                return {
                    **state,
                    "next_route": "CHATBOT",
                    "pending_tools": ["query_asset_database", "create_visualization"],
                    "multi_tool_guidance": f"""
🎯 CRITICAL MULTI-TOOL INSTRUCTION:
User requested: "{user_query[:100]}..."

MISSING TOOLS:
❌ Data retrieval tool (query_asset_database)
❌ Visualization tool (create_visualization)

MANDATORY SEQUENCE:
1. First use query_asset_database to get data
2. Then use create_visualization to make chart

FORCE USE: query_asset_database first."""
                }
            else:
                print("   ➡️ All required tools used - routing to final response")
                print(
                    f"   🔧 DEBUG: Setting next_route=FINAL_RESPONSE, both tools completed")
                return {
                    **state,
                    "next_route": "FINAL_RESPONSE",
                    "pending_tools": [],
                    "multi_tool_guidance": ""
                }
        else:
            print("   ➡️ Single tool workflow - routing to final response")
            print(f"   🔧 DEBUG: Setting next_route=FINAL_RESPONSE, single tool workflow")
            return {
                **state,
                "next_route": "FINAL_RESPONSE",
                "pending_tools": [],
                "multi_tool_guidance": ""
            }

    def route_after_quality_check(state: State) -> str:
        """📊 Route after quality check - determines next step."""
        quality_result = state.get("quality_check_result", "INSUFFICIENT")
        retry_count = state.get("retry_count", 0)
        max_retries = 3

        if quality_result == "SUFFICIENT":
            print(f"✅ Quality sufficient - ending workflow")
            return "END"
        elif retry_count >= max_retries:
            print(
                f"⚠️ Max retries ({max_retries}) reached - ending with current response")
            return "END"
        else:
            print(
                f"🔄 Quality insufficient - routing to reflection (retry {retry_count}/{max_retries})")
            return "REFLECTION"    # Build the graph
    print("🏗️ Building agent graph structure...")
    debug_logger.log_step(node_name="build_graph",
                          step_type="NODE_ENTRY",
                          description="Building agent graph with nodes and edges",
                          data={
                                      "tools_count": len(tools),
                                      "tool_names": [tool.name for tool in tools],
                                      "graph_version": "v2.3"
                          }
                          )

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = BasicToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    def route_from_multi_tool(state: State) -> str:
        """Router function untuk multi-tool workflow"""
        # Get the routing decision from the most recent message or state
        messages = state.get("messages", [])

        # Check if there's a routing decision in the state
        next_route = state.get("next_route", "FINAL_RESPONSE")
        pending_tools = state.get("pending_tools", [])
        multi_tool_guidance = state.get("multi_tool_guidance", "")

        print(f"🔀 Routing from multi_tool_router:")
        print(f"   next_route from state: {next_route}")
        print(f"   pending_tools from state: {pending_tools}")
        print(f"   has_guidance from state: {bool(multi_tool_guidance)}")
        print(f"   🔧 FULL STATE DEBUG: {list(state.keys())}")

        # CRITICAL FIX: Check the messages to determine if we need visualization
        # This is a fallback when state is not properly passed
        if not pending_tools:
            # Analyze the current state to determine routing
            user_query = ""
            tools_used = []

            for msg in messages:
                if hasattr(msg, 'type') and msg.type == 'human':
                    user_query = msg.content.lower()
                elif hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name'):
                    tools_used.append(msg.name)

            # Multi-tool detection logic (same as in multi_tool_router)
            needs_data = any(word in user_query for word in [
                'berapa', 'data', 'jumlah', 'total', 'hc per', 'headcount'
            ])
            needs_visualization = any(word in user_query for word in [
                'grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram',
                'buatkan grafik', 'buat grafik', 'batang'
            ])

            data_tools_used = any(tool in tools_used for tool in [
                'query_asset_database', 'sql_agent'
            ])
            viz_tool_used = 'create_visualization' in tools_used

            print(f"   🔧 FALLBACK ANALYSIS:")
            print(
                f"      needs_data: {needs_data}, needs_viz: {needs_visualization}")
            print(
                f"      data_tools_used: {data_tools_used}, viz_tool_used: {viz_tool_used}")
            print(f"      tools_used: {tools_used}")

            # Make routing decision based on analysis
            if needs_data and needs_visualization and data_tools_used and not viz_tool_used:
                print(
                    f"   🔧 FALLBACK OVERRIDE: Forcing route to CHATBOT for visualization")
                return "CHATBOT"

        # If we have pending tools, we should route to CHATBOT regardless of what next_route says
        if pending_tools and len(pending_tools) > 0:
            print(
                f"   🔧 OVERRIDE: Found pending tools {pending_tools}, forcing route to CHATBOT")
            return "CHATBOT"

        # Otherwise use the next_route from state
        print(f"   ✅ Using next_route from state: {next_route}")
        return next_route

    # Tambahkan node untuk workflow baru
    graph_builder.add_node("multi_tool_router", multi_tool_router)
    graph_builder.add_node("final_response_generator",
                           final_response_generator)
    graph_builder.add_node("final_response_checker", final_response_checker)
    graph_builder.add_node("reflection_node", reflection_node)

    # Setup edges dengan workflow baru
    # START → chatbot → route_tools → tools → multi_tool_router → [chatbot/final_response_generator] → final_response_checker → [finish/reflection]
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {
            "tools": "tools",
            "__end__": "__end__",
        },
    )

    # Setelah tools, ke multi_tool_router untuk cek apakah perlu tools lagi
    graph_builder.add_edge("tools", "multi_tool_router")

    # Dari multi_tool_router, bisa ke chatbot (untuk tool lagi) atau final_response_generator
    graph_builder.add_conditional_edges(
        "multi_tool_router",
        route_from_multi_tool,
        {
            "CHATBOT": "chatbot",
            "FINAL_RESPONSE": "final_response_generator",
        },
    )

    # Setelah final response generator, ke final response checker
    graph_builder.add_edge("final_response_generator",
                           "final_response_checker")    # Dari final response checker, routing ke reflection atau finish
    graph_builder.add_conditional_edges(
        "final_response_checker",
        route_after_quality_check,
        {
            "REFLECTION": "reflection_node",
            "END": "__end__",
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
