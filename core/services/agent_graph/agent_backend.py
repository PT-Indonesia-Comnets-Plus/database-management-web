import json
import time
from IPython.display import Image, display
from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import ToolMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from .debug_logger import debug_logger


class Reflection(BaseModel):
    """Schema untuk hasil refleksi agen terhadap output tool sebelumnya.

    Attributes:
        is_sufficient (bool): Apakah hasil tool sudah cukup untuk menjawab pertanyaan
        critique (str): Kritik terhadap hasil tool
        next_action (str): Tindakan selanjutnya - "FINISH" atau "RETRY"
        suggested_tool (Optional[str]): Tool yang disarankan untuk retry (jika ada)
        reasoning (str): Alasan untuk keputusan yang diambil
    """
    is_sufficient: bool
    critique: str
    next_action: Literal["FINISH", "RETRY"]
    suggested_tool: Optional[str] = None
    reasoning: str


class State(TypedDict):
    """Represents the state structure containing a list of messages and reflection results.

    Attributes:
        messages (list): A list of messages, where each message can be processed
        by adding messages using the `add_messages` function.
        reflection (Optional[Reflection]): Hasil refleksi dari supervisor agent
        retry_count (int): Jumlah retry yang sudah dilakukan untuk mencegah infinite loop
        final_response (Optional[str]): Final response yang dihasilkan oleh final_response_generator
        response_quality (Optional[str]): Kualitas response ("SUFFICIENT" atau "INSUFFICIENT")
        needs_reflection (Optional[bool]): Apakah perlu reflection setelah final response check
        evaluation_details (Optional[str]): Detail evaluasi dari final_response_checker
    """
    messages: Annotated[list, add_messages]
    reflection: Optional[Reflection]
    retry_count: int
    final_response: Optional[str]
    response_quality: Optional[str]
    needs_reflection: Optional[bool]
    evaluation_details: Optional[str]


class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage.

    This class retrieves tool calls from the most recent AIMessage in the input
    and invokes the corresponding tool to generate responses.

    Attributes:
        tools_by_name (dict): A dictionary mapping tool names to tool instances.
    """

    def __init__(self, tools: list) -> None:
        """Initializes the BasicToolNode with available tools.

        Args:
            tools (list): A list of tool objects, each having a `name` attribute.
        """
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        """Executes the tools based on the tool calls in the last message.

        Args:
            inputs (dict): A dictionary containing the input state with messages.

        Returns:
            dict: A dictionary with a list of `ToolMessage` outputs.

        Raises:
            ValueError: If no messages are found in the input.
        """
        # 🔍 DEBUG: Log tool node entry
        debug_logger.log_node_entry("tools", {
            "messages_count": len(inputs.get("messages", [])),
            "has_messages": bool(inputs.get("messages", []))
        })

        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            debug_logger.log_error("tools", ValueError("No message found in input"), {
                "inputs_keys": list(inputs.keys())
            })
            raise ValueError("No message found in input")

        outputs = []

        # 🔍 DEBUG: Log tool calls detection
        tool_calls = getattr(message, 'tool_calls', [])
        debug_logger.log_step(
            node_name="tools",
            step_type="TOOL_CALL",
            description=f"Processing {len(tool_calls)} tool calls",
            data={
                "tool_calls_count": len(tool_calls),
                "tool_names": [call.get("name", "unknown") for call in tool_calls]
            }
        )

        for tool_call in message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 🔍 DEBUG: Log individual tool execution start
            tool_start_time = time.time()
            debug_logger.log_tool_call(
                tool_name=tool_name,
                tool_args=tool_args
            )

            try:
                tool_result = self.tools_by_name[tool_name].invoke(tool_args)
                tool_duration = (time.time() - tool_start_time) * 1000

                # 🔍 DEBUG: Log tool success
                debug_logger.log_tool_result(
                    tool_name=tool_name,
                    result=tool_result,
                    success=True
                )

                # Prepare content for ToolMessage
                # If tool_result is already a string (e.g., from create_visualization), use it directly.
                # Otherwise, assume it's a dict/list and dump to JSON string.
                if isinstance(tool_result, str):
                    content_for_message = tool_result
                else:
                    content_for_message = json.dumps(tool_result)

                outputs.append(
                    ToolMessage(
                        content=content_for_message,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

            except Exception as e:
                tool_duration = (time.time() - tool_start_time) * 1000

                # 🔍 DEBUG: Log tool error
                debug_logger.log_tool_result(
                    tool_name=tool_name,
                    result=None,
                    success=False,
                    error_message=str(e)
                )

                # Create error message for tool output
                error_content = f"Error executing {tool_name}: {str(e)}"
                outputs.append(
                    ToolMessage(
                        content=error_content,
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

        # 🔍 DEBUG: Log tool node completion
        debug_logger.log_step(
            node_name="tools",
            step_type="NODE_COMPLETION",
            description=f"Tools execution completed - {len(outputs)} results",
            data={
                "outputs_count": len(outputs),
                "successful_tools": len([o for o in outputs if not o.content.startswith("Error")])
            }
        )

        return {"messages": outputs}


def route_tools(
    state: State,
) -> Literal["tools", "__end__"]:
    """

    Determines whether to route to the ToolNode or end the flow.

    This function is used in the conditional_edge and checks the last message in the state for tool calls. If tool
    calls exist, it routes to the 'tools' node; otherwise, it routes to the end.

    Args:
        state (State): The input state containing a list of messages.

    Returns:
        Literal["tools", "__end__"]: Returns 'tools' if there are tool calls;
        '__end__' otherwise.

    Raises:
        ValueError: If no messages are found in the input state.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(
            f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"


def plot_agent_schema(graph):
    """Plots the agent schema using a graph object, if possible.

    Tries to display a visual representation of the agent's graph schema
    using Mermaid format and IPython's display capabilities. If the required
    dependencies are missing, it catches the exception and prints a message
    instead.

    Args:
        graph: A graph object that has a `get_graph` method, returning a graph
        structure that supports Mermaid diagram generation.

    Returns:
        None
    """
    try:
        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception:
        # This requires some extra dependencies and is optional
        return print("Graph could not be displayed.")


def reflection_node(state: State) -> dict:
    """
    ULTRA STRICT Reflection Node - Memaksa penggunaan tool yang tepat
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    # 🔍 DEBUG: Log reflection node entry
    debug_logger.log_node_entry("reflection_node", {
        "messages_count": len(state.get("messages", [])),
        "retry_count": state.get("retry_count", 0),
        "has_previous_reflection": bool(state.get("reflection"))
    })

    print("🔍 Running ULTRA STRICT Reflection Node...")

    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    if not messages:
        debug_logger.log_error("reflection_node", ValueError("No messages to analyze"), {
            "state_keys": list(state.keys())
        })
        return {
            "reflection": Reflection(
                is_sufficient=False,
                critique="No messages to analyze",
                next_action="RETRY",
                reasoning="Tidak ada pesan untuk dianalisis",
                suggested_tool=None
            ),
            "retry_count": retry_count + 1
        }

    # Get last human message untuk mengetahui pertanyaan user
    last_human_message = None
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_human_message = msg
            break

    if not last_human_message:
        debug_logger.log_error("reflection_node", ValueError("No user question found"), {
            "total_messages": len(messages),
            "message_types": [getattr(msg, 'type', 'unknown') for msg in messages[-3:]]
        })
        return {
            "reflection": Reflection(
                is_sufficient=False,
                next_action="RETRY",
                critique="No user question found",
                reasoning="Tidak ditemukan pertanyaan user",
                suggested_tool=None
            ),
            "retry_count": retry_count + 1
        }

    user_question = last_human_message.content.lower()
    print(f"🎯 Analyzing user question: {user_question}")

    # 🔍 DEBUG: Log user query analysis
    debug_logger.log_step(
        node_name="reflection_node",
        step_type="REFLECTION",
        description="Analyzing user query for tool validation",
        data={
            "user_question": user_question[:100] + "..." if len(user_question) > 100 else user_question,
            "question_length": len(user_question),
            "retry_count": retry_count
        }
    )

    # Check if any tools were called
    ai_messages = [msg for msg in messages if hasattr(
        msg, 'type') and msg.type == 'ai']
    last_ai_message = ai_messages[-1] if ai_messages else None

    if not last_ai_message:
        return {
            "reflection": Reflection(
                is_sufficient=False,
                next_action="RETRY",
                critique="No AI response found",
                reasoning="Tidak ada respons AI ditemukan",
                suggested_tool=None),
            "retry_count": retry_count + 1
        }

    tool_calls = getattr(last_ai_message, 'tool_calls', [])

    # ULTRA STRICT VALIDATION dengan keyword detection - PRIORITAS BERURUTAN
    def detect_required_tool(question):
        """Deteksi tool yang WAJIB digunakan berdasarkan kata kunci dengan prioritas"""
        q = question.lower()

        # PRIORITAS 0: SPREADSHEET (trigger_spreadsheet_etl_and_get_summary) - Check first for specific spreadsheet contexts
        spreadsheet_keywords = ['spreadsheet',
                                'excel', 'upload', 'etl', 'file']
        spreadsheet_actions = ['ambil data', 'ambil file',
                               'proses data', 'update data', 'get data dari spreadsheet']

        # Context-aware detection for spreadsheet operations
        if any(kw in q for kw in spreadsheet_keywords) or any(action in q for action in spreadsheet_actions):
            return 'trigger_spreadsheet_etl_and_get_summary', 'SPREADSHEET'

        # Special case: "data terbaru" in spreadsheet context
        if 'data terbaru' in q and any(context in q for context in ['spreadsheet', 'file', 'ambil']):
            return 'trigger_spreadsheet_etl_and_get_summary', 'SPREADSHEET'

        # PRIORITAS 1: INTERNET SEARCH (tavily_search_results_json) - Only for clear internet research
        internet_keywords = ['tesla', 'juara', 'ucl', 'berita', 'cuaca', 'internet', 'informasi umum',
                             'carikan di internet', 'cari di internet', 'tahun berapa terbentuk', 'didirikan',
                             'kapan', 'siapa pendiri', 'founded', 'established']
        # Only trigger internet search if it's clearly NOT about internal data/spreadsheets
        if any(kw in q for kw in internet_keywords) and not any(internal in q for internal in ['spreadsheet', 'data internal', 'ambil data', 'file']):
            return 'tavily_search_results_json', 'INTERNET SEARCH'
          # PRIORITAS 2: VISUALISASI (create_visualization) - Tapi cek apakah butuh data dulu
        viz_keywords = ['grafik', 'chart', 'visualisasi',
                        'pie', 'bar', 'diagram', 'buat grafik', 'pie chart']
        has_viz_request = any(kw in q for kw in viz_keywords)

        # Jika ada request visualisasi DAN data teknis, maka perlu kedua tool
        if has_viz_request:
            # Cek apakah butuh data dari database dulu
            needs_data = any(data_kw in q for data_kw in [
                             'berapa', 'jumlah', 'bandingkan', 'total', 'olt', 'pelanggan', 'kota'])
            if needs_data:
                # Untuk visualisasi yang butuh data, prioritaskan get data dulu
                return 'query_asset_database', 'VISUALISASI_WITH_DATA'
            else:
                return 'create_visualization', 'VISUALISASI'

        # PRIORITAS 3: DATA DATABASE (query_asset_database) - Kata kerja data
        db_keywords = ['berapa', 'total', 'jumlah', 'bandingkan', 'hitung', 'cari data', 'data',
                       'pelanggan', 'brand', 'kota', 'cluster', 'lokasi', 'aset']
        if any(kw in q for kw in db_keywords):
            # PRIORITAS 4: DOKUMENTASI TEKNIS - Untuk definisi dan penjelasan konsep
            return 'query_asset_database', 'DATA DATABASE'
        doc_pure_keywords = ['apa itu fat', 'apa itu fdt', 'perbedaan fat fdt', 'hubungan fat',
                             'cara instalasi', 'panduan', 'sop', 'dokumentasi', 'konfigurasi',
                             'apa perbedaan', 'perbedaan antara', 'berbeda dari', 'definisi']
        if any(kw in q for kw in doc_pure_keywords):
            return 'search_internal_documents', 'DOKUMENTASI TEKNIS'

        # DEFAULT: Jika menyebutkan komponen teknis tapi ada kata kerja data -> DATABASE
        if any(tech in q for tech in ['olt', 'fat', 'fdt']) and any(action in q for action in ['berapa', 'jumlah', 'bandingkan', 'total']):
            return 'query_asset_database', 'DATA DATABASE'

        return None, 'UNKNOWN'

    required_tool, question_category = detect_required_tool(user_question)
    tools_used = [call.get('name', 'unknown')
                  for call in tool_calls] if tool_calls else []

    print(f"📊 Question category: {question_category}")
    print(f"🔧 Required tool: {required_tool}")
    # ULTRA STRICT EVALUATION dengan logic khusus untuk visualisasi
    print(f"⚙️ Tools used: {tools_used}")
    is_correct = False
    critique = ""
    suggested_tool = required_tool

    if not tool_calls:
        # NO TOOLS USED - MAJOR ERROR - FORCE TOOL USAGE
        is_correct = False
        if required_tool:
            critique = f"CRITICAL ERROR: WAJIB menggunakan tool {required_tool} untuk kategori {question_category}! Tidak boleh jawab langsung."
            suggested_tool = required_tool
        else:
            # Fallback ke search_internal_documents untuk query yang tidak jelas
            critique = f"CRITICAL ERROR: WAJIB menggunakan tools! Coba search_internal_documents untuk mencari konteks."
            suggested_tool = 'search_internal_documents'

    elif question_category == 'VISUALISASI_WITH_DATA':
        # SPECIAL CASE: Visualisasi yang butuh data
        # Step 1: Harus ada query_asset_database atau sql_agent untuk get data
        # Step 2: Kemudian create_visualization untuk buat chart

        has_data_tool = any(tool in tools_used for tool in [
                            'query_asset_database', 'sql_agent'])
        has_viz_tool = 'create_visualization' in tools_used

        if has_data_tool and not has_viz_tool:
            # Bagus! Sudah ambil data, sekarang perlu visualisasi
            is_correct = False
            critique = f"GOOD PROGRESS: Data retrieved with {tools_used}, now need create_visualization for chart"
            suggested_tool = 'create_visualization'
        elif has_data_tool and has_viz_tool:
            # Perfect! Sudah lengkap
            is_correct = True
            critique = f"PERFECT: Complete visualization flow - data + chart created"
        elif has_viz_tool and not has_data_tool:
            # Salah urutan - bikin chart tanpa data
            is_correct = False
            critique = f"WRONG ORDER: Created visualization without data. Need query_asset_database first"
            suggested_tool = 'query_asset_database'
        else:
            # Pakai tool yang salah total
            is_correct = False
            critique = f"WRONG TOOL: Visualization with data needs query_asset_database + create_visualization, got {tools_used}"
            suggested_tool = 'query_asset_database'

    elif required_tool and required_tool not in tools_used:
        # WRONG TOOL USED
        is_correct = False
        critique = f"WRONG TOOL: Kategori {question_category} memerlukan {required_tool}, tapi menggunakan {tools_used}"

    elif required_tool and required_tool in tools_used:
        # CORRECT TOOL USED - Check result quality AND completeness
        tool_messages = [msg for msg in messages if hasattr(
            msg, 'type') and msg.type == 'tool']
        if tool_messages:
            # Check for error indicators
            last_tool_result = tool_messages[-1].content.lower()
            error_indicators = ['error', 'gagal',
                                'tidak dapat', 'failed', 'connection', 'timeout']
            if any(indicator in last_tool_result for indicator in error_indicators):
                is_correct = False
                critique = f"Tool {required_tool} used correctly but returned error: {last_tool_result[:100]}..."
            else:
                is_correct = True
                critique = f"CORRECT: Tool {required_tool} tepat untuk kategori {question_category}"
        else:
            is_correct = True
            critique = f"CORRECT: Tool {required_tool} tepat untuk kategori {question_category}"
    else:        # FALLBACK - Tidak dapat mendeteksi kategori
        # ALWAYS ensure some tool is used for UNKNOWN categories
        if not tools_used:
            # No tools used - FORCE fallback to web research
            is_correct = False
            critique = f"UNKNOWN CATEGORY: No tools used - forcing tools_web_search as fallback"
            suggested_tool = 'tools_web_search'
        elif 'tools_web_search' in tools_used and len(tools_used) == 1:
            # Only web search used - this is fine for unknown queries
            is_correct = True
            critique = f"UNKNOWN CATEGORY: Web search tool used appropriately"
        else:
            # Some actual tools were used
            is_correct = True
            critique = f"UNKNOWN CATEGORY: Tools used {tools_used} - proceeding"

    print(f"📋 Evaluation: {critique}")
    print(f"✅ Is correct: {is_correct}")

    # Create reflection result
    reflection_result = Reflection(
        is_sufficient=is_correct,
        critique=critique,
        next_action="FINISH" if is_correct else "RETRY",
        # Only suggest tool if correction needed
        suggested_tool=suggested_tool if not is_correct else None,
        reasoning=f"Tool evaluation for {question_category} - {'CORRECT' if is_correct else 'INCORRECT'}"
    )

    # 🔍 DEBUG: Log reflection result
    debug_logger.log_reflection(
        reflection_result=reflection_result,
        suggested_tool=suggested_tool
    )

    debug_logger.log_step(
        node_name="reflection_node",
        step_type="REFLECTION",
        description=f"Reflection analysis complete: {reflection_result.next_action}",
        data={
            "is_sufficient": reflection_result.is_sufficient,
            "next_action": reflection_result.next_action,
            "suggested_tool": reflection_result.suggested_tool,
            "question_category": question_category,
            "tools_evaluated": tools_used,
            "critique_summary": critique[:100] + "..." if len(critique) > 100 else critique
        }
    )

    print(
        f"🔍 ULTRA STRICT Reflection result: sufficient={reflection_result.is_sufficient}, action={reflection_result.next_action}")

    return {
        "reflection": reflection_result,
        "retry_count": retry_count
    }


def should_retry_or_finish(state: State) -> Literal["chatbot", "__end__"]:
    """
    Conditional edge function yang menentukan apakah harus retry atau finish.
    Includes intelligent retry logic and max retry protection.

    Args:
        state (State): State saat ini

    Returns:
        str: "chatbot" untuk retry, "__end__" untuk finish
    """
    reflection = state.get("reflection")
    retry_count = state.get("retry_count", 0)

    # 🔍 DEBUG: Log routing decision entry
    debug_logger.log_node_entry("should_retry_or_finish", {
        "retry_count": retry_count,
        "has_reflection": bool(reflection),
        "reflection_action": getattr(reflection, 'next_action', None) if reflection else None,
        "reflection_sufficient": getattr(reflection, 'is_sufficient', None) if reflection else None
    })

    # Batasi maksimal retry untuk mencegah infinite loop
    MAX_RETRIES = 2

    print(
        f"🤔 Should retry or finish? Current retry count: {retry_count}/{MAX_RETRIES}")

    if not reflection:
        print("🏁 No reflection found, finishing...")
        decision = "__end__"
        debug_logger.log_decision(
            decision_point="no_reflection",
            decision=decision,
            reasoning="No reflection found in state"
        )
        return decision

    if retry_count >= MAX_RETRIES:
        print(f"🔄 Max retries ({MAX_RETRIES}) reached, finishing...")
        decision = "__end__"
        debug_logger.log_decision(
            decision_point="max_retries_reached",
            decision=decision,
            reasoning=f"Maximum retries ({MAX_RETRIES}) exceeded"
        )
        return decision

    if reflection.next_action == "RETRY" and not reflection.is_sufficient:
        print(f"🔄 Retrying... (attempt {retry_count + 1}/{MAX_RETRIES})")
        print(f"   Reason: {reflection.critique}")
        if reflection.suggested_tool:
            print(f"   Suggested tool: {reflection.suggested_tool}")
        decision = "chatbot"
        debug_logger.log_decision(
            decision_point="reflection_retry",
            decision=decision,
            reasoning=f"Reflection suggests retry with tool: {reflection.suggested_tool}"
        )
        return decision

    elif reflection.next_action == "FINISH" and reflection.is_sufficient:
        # Check if this is a complete answer that doesn't need final response generation
        if "COMPLETE:" in reflection.critique and "no final response needed" in reflection.critique.lower():
            print("🎯 Tool returned complete answer - ending directly!")
            decision = "__end__"
            debug_logger.log_decision(
                decision_point="complete_answer_direct_end",
                decision=decision,
                reasoning="Tool provided ready-to-use complete answer, no LLM final response needed"
            )
            return decision
        else:
            print("🔄 Creating final response from tool results...")
            decision = "chatbot"  # Create final response for incomplete/formatted results
            debug_logger.log_decision(
                decision_point="create_final_response",
                decision=decision,
                reasoning="Tools executed successfully, creating final response"
            )
            return decision
    else:
        print("🏁 Reflection indicates completion, finishing...")
        if reflection.is_sufficient:
            print("   ✅ Task completed successfully")
        else:
            print("   ⚠️ Task incomplete but max retries reached")
        decision = "__end__"
        debug_logger.log_decision(
            decision_point="reflection_completion",
            decision=decision,
            reasoning=f"Task {'completed' if reflection.is_sufficient else 'incomplete'}"
        )
        return decision
