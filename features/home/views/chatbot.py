import streamlit as st
import warnings
import os
import time  # Tetap dibutuhkan untuk typing animation
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
import plotly.graph_objects as go
import json
from core.services.agent_graph.build_graph import build_graph
from typing import Any
from core.utils.load_css import load_custom_css
warnings.filterwarnings('ignore')


def display_message_with_typing_animation(placeholder, message: str, typing_speed: float = 0.02) -> None:
    """
    Menampilkan pesan assistant dengan efek animasi mengetik karakter per karakter.

    Args:
        placeholder: Streamlit placeholder untuk output teks.
        message (str): Pesan yang akan ditampilkan.
        typing_speed (float, optional): Kecepatan mengetik per karakter. Default 0.02.
    """
    displayed_message = ""
    lines = message.split('\n')
    for i, line in enumerate(lines):
        if i > 0:
            placeholder.markdown(displayed_message + "\n",
                                 unsafe_allow_html=True)
            time.sleep(typing_speed * 5)
        for char in line:
            displayed_message += char
            placeholder.markdown(displayed_message, unsafe_allow_html=True)
            time.sleep(typing_speed)
        if i < len(lines) - 1:
            displayed_message += "\n"
    placeholder.markdown(displayed_message, unsafe_allow_html=True)


def _render_message_content(message_obj: Any, target_container: st, is_streaming_final_output: bool = False, is_production: bool = True):
    """
    Merender konten dari satu objek pesan (AIMessage, ToolMessage) ke dalam container Streamlit.

    Args:
        message_obj: Objek pesan LangChain (AIMessage, ToolMessage).
        target_container: Container Streamlit (st atau st.empty()) tempat merender.
        is_streaming_final_output: True jika ini adalah output teks AI terakhir yang harus dianimasikan.
        is_production: True jika ingin menyembunyikan output tool mentah.
    """
    content = message_obj.content

    if isinstance(message_obj, AIMessage):
        if hasattr(message_obj, 'tool_calls') and message_obj.tool_calls:
            tool_names = [tc['name'] for tc in message_obj.tool_calls]
            target_container.markdown(
                f"⚙️ *Menggunakan tool: {', '.join(tool_names)}...*", unsafe_allow_html=True)  # Tetap tampilkan info penggunaan tool

        # Konten AIMessage (respons teks dari LLM) selalu ditampilkan
        if content and content.strip():
            if is_streaming_final_output:
                # Buat placeholder khusus untuk animasi ini di dalam target_container
                animation_placeholder = target_container.empty()
                display_message_with_typing_animation(
                    animation_placeholder, content)
            else:
                target_container.markdown(content, unsafe_allow_html=True)

    elif isinstance(message_obj, ToolMessage):
        tool_name = message_obj.name
        # Membuat key unik untuk plotly_chart berdasarkan tool_call_id jika ada
        chart_key = None
        if hasattr(message_obj, 'tool_call_id') and message_obj.tool_call_id:
            chart_key = f"plotly_chart_{tool_name}_{message_obj.tool_call_id}"
        else:
            # Fallback key jika tool_call_id tidak ada (seharusnya jarang terjadi untuk visualisasi)
            chart_key = f"plotly_chart_{tool_name}_{hash(content)}"

        try:
            parsed_content = json.loads(content)
            if tool_name == "create_visualization" and isinstance(parsed_content, dict) and "data" in parsed_content and "layout" in parsed_content:
                try:
                    fig = go.Figure(parsed_content)
                    # Tambahkan argumen key yang unik
                    target_container.plotly_chart(
                        fig, use_container_width=True, key=chart_key)
                except Exception as e:
                    if not is_production:  # Tampilkan detail error hanya jika bukan production
                        with target_container.expander(f"Raw Output dari `{tool_name}` (Error Visualisasi)"):
                            target_container.json(parsed_content)
            elif isinstance(parsed_content, dict) and parsed_content.get("error"):
                # Jika tool mengembalikan JSON dengan field "error"
                # Di production, biarkan LLM yang menyampaikan error ini jika relevan
                if not is_production:
                    target_container.error(
                        f"Error dari tool `{tool_name}`: {parsed_content['error']}")
                    with target_container.expander(f"Detail Error dari `{tool_name}`"):
                        target_container.json(parsed_content)
            elif not is_production:  # Tampilkan output JSON/teks dari tool lain hanya jika bukan production
                with target_container.expander(f"Output dari `{tool_name}` (JSON)"):
                    target_container.json(parsed_content)
        except (json.JSONDecodeError, TypeError):
            # Konten bukan JSON, tampilkan sebagai teks
            if not is_production:  # Tampilkan output teks dari tool lain hanya jika bukan production
                with target_container.expander(f"Output dari `{tool_name}` (Teks)"):
                    target_container.text(content)


def initialize_messages() -> None:
    """
    Inisialisasi riwayat pesan dalam session_state jika belum ada.
    """
    if "messages" not in st.session_state or not isinstance(st.session_state.messages, list):
        st.session_state.messages = []
        st.session_state.messages.append(
            AIMessage(
                content="Halo! Ada yang bisa saya bantu terkait aset atau dokumen ICONNET?")
        )
    if "processing_turn" not in st.session_state:
        st.session_state.processing_turn = False
    if "current_turn_messages" not in st.session_state:  # Pesan untuk giliran AI saat ini
        st.session_state.current_turn_messages = []


def display_all_messages_history():
    """Menampilkan semua pesan dari st.session_state.messages."""
    if "messages" not in st.session_state:
        return

    current_assistant_messages_block = []

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            # Jika ada blok pesan asisten sebelumnya, render dulu
            if current_assistant_messages_block:
                with st.chat_message("assistant"):
                    for assistant_msg in current_assistant_messages_block:
                        _render_message_content(
                            assistant_msg, st, is_streaming_final_output=False, is_production=True)  # is_production=True
                current_assistant_messages_block = []
            # Tampilkan pesan pengguna
            with st.chat_message("user"):
                st.markdown(f"**{msg.content}**", unsafe_allow_html=True)
        elif isinstance(msg, (AIMessage, ToolMessage)):
            current_assistant_messages_block.append(msg)

    # Render blok pesan asisten terakhir jika ada (misalnya, pesan sapaan awal)
    if current_assistant_messages_block:
        with st.chat_message("assistant"):
            for assistant_msg in current_assistant_messages_block:
                _render_message_content(
                    assistant_msg, st, is_streaming_final_output=False, is_production=True)  # is_production=True


def process_user_input(graph, config) -> None:
    """
    Memproses input pengguna, mengelola interaksi dengan agent graph,
    dan menampilkan respons secara incremental.

    Args:
        graph: Graph agent untuk memproses pesan.
        config (dict): Konfigurasi untuk stream graph.
    """
    prompt = st.chat_input(
        "Tanyakan tentang aset, dokumen, atau informasi umum...",
        disabled=st.session_state.get("processing_turn", False),
        key="chat_input_main"
    )
    # Define the system prompt
    system_prompt_text = """
    Anda adalah ICONNET Assistant, sebuah AI yang membantu pengguna mencari informasi terkait data aset ICONNET,
    dokumen internal, dan informasi umum dari internet.

    Anda memiliki akses ke beberapa tools:
    1. `query_asset_database`: Gunakan ini untuk pertanyaan spesifik tentang data aset yang ada di database, seperti jumlah aset di kota tertentu, detail FAT ID, atau ringkasan data numerik.
    2. `search_internal_documents`: Gunakan ini untuk mencari informasi dalam dokumen internal perusahaan (SOP, panduan, laporan) terkait prosedur, definisi, atau penjelasan.
    3. `tavily_search_tool`: Gunakan ini untuk mencari informasi umum dari internet yang tidak ada di database atau dokumen internal.
    4. `create_visualization`: Gunakan ini JIKA PENGGUNA MEMINTA SECARA EKSPLISIT untuk membuat grafik atau visualisasi.
        - LANGKAH PENTING: Anda HARUS mendapatkan data terlebih dahulu menggunakan tool lain (misalnya, `query_asset_database`).
        - Setelah mendapatkan data (misalnya, dari `query_asset_database` dalam bentuk teks seperti "Kota A: 10, Kota B: 20" atau daftar), Anda WAJIB MENGUBAH data tersebut ke format `data_json` yang benar.
        - Format `data_json` adalah STRING JSON dari LIST OF DICTIONARIES. Contoh: Jika data adalah 'Surabaya: 100 HC, Malang: 80 HC', maka `data_json` harus menjadi: `'[{"nama_kota": "Surabaya", "jumlah_hc": 100}, {"nama_kota": "Malang", "jumlah_hc": 80}]'`. Anda harus menentukan nama kolom yang sesuai (misal "nama_kota", "jumlah_hc").
        - Tentukan juga `chart_type` (misal "bar", "line"), `x_column` (kolom untuk sumbu X, misal "nama_kota"), dan `y_column` (kolom untuk sumbu Y, misal "jumlah_hc").
        - Tool ini akan menghasilkan spesifikasi chart Plotly JSON jika berhasil.

    ALUR KERJA UNTUK VISUALISASI:
    1. Jika pengguna meminta visualisasi (misal "buat bar chart total HC per kota"):
    2. Identifikasi data apa yang dibutuhkan (misal "total HC per kota").
    3. Gunakan tool yang sesuai untuk mendapatkan data tersebut (misal `query_asset_database`).
    4. Ambil hasil dari tool data. Jika hasilnya berupa teks narasi atau tabel sederhana, EKSTRAK dan TRANSFORMASIKAN data tersebut menjadi format `data_json` seperti dijelaskan di atas. Ini adalah TANGGUNG JAWAB ANDA.
    5. Panggil tool `create_visualization` dengan `data_json` yang sudah Anda siapkan, beserta `chart_type`, `x_column`, `y_column`, dan `title` yang sesuai.
    6. Jika `create_visualization` berhasil, sampaikan bahwa Anda telah membuat visualisasi. Jika gagal, sampaikan pesan error dari tool tersebut dengan sopan.

    Prioritaskan penggunaan `query_asset_database` atau `search_internal_documents` jika pertanyaan jelas terkait data atau dokumen internal. Gunakan `tavily_search_tool` hanya jika pertanyaan bersifat umum atau tidak dapat dijawab dari sumber internal.

    Anda mungkin perlu menggunakan lebih dari satu tool untuk menjawab pertanyaan yang kompleks. Setelah mengumpulkan informasi yang cukup dari semua tool yang relevan, rangkum hasilnya dan berikan jawaban yang komprehensif, jelas, dan mudah dipahami kepada pengguna.
    Jika hasil dari satu tool belum cukup, pertimbangkan untuk menggunakan tool lain sebelum memberikan jawaban akhir.
    """

    if prompt and not st.session_state.get("processing_turn", False):
        user_message = HumanMessage(content=prompt)
        st.session_state.messages.append(user_message)
        st.session_state.processing_turn = True
        st.session_state.current_turn_messages = []  # Reset untuk giliran baru
        st.rerun()

    if st.session_state.get("processing_turn", False):
        # Pesan pengguna terakhir sudah ditampilkan oleh display_all_messages_history pada rerun
        # Sekarang kita buat bubble untuk asisten
        with st.chat_message("assistant"):
            # Placeholder untuk seluruh giliran asisten
            assistant_turn_placeholder = st.empty()

            try:
                # Persiapkan pesan untuk dikirim ke graph
                # Kita hanya mengirim pesan pengguna terbaru. LangGraph & MemorySaver akan menangani histori.
                last_human_message = next((m for m in reversed(
                    st.session_state.messages) if isinstance(m, HumanMessage)), None)
                if not last_human_message:
                    # Seharusnya tidak terjadi jika processing_turn True setelah prompt
                    st.session_state.processing_turn = False
                    st.rerun()
                    return

                messages_for_graph_invocation = []
                # Cek apakah ini interaksi pertama pengguna setelah sapaan AI
                # (yaitu, hanya ada 1 HumanMessage sejauh ini)
                if len([m for m in st.session_state.messages if isinstance(m, HumanMessage)]) == 1:
                    messages_for_graph_invocation.append(
                        SystemMessage(content=system_prompt_text))

                messages_for_graph_invocation.append(last_human_message)

                # Tampilkan "Thinking..." di awal
                if not st.session_state.current_turn_messages:
                    with assistant_turn_placeholder.container():
                        st.markdown("🤔 Memproses permintaan Anda...")

                # Streaming dari graph
                # `st.session_state.messages` adalah history UI kita.
                # `event.get("messages")` adalah history dari state graph.
                count_history_ui_before_stream = len(st.session_state.messages)

                events = graph.stream(
                    {"messages": messages_for_graph_invocation},
                    config,
                    stream_mode="values"
                )

                for event in events:
                    all_messages_from_graph_state = event.get("messages", [])

                    # Identifikasi pesan baru dari agent
                    new_agent_messages_from_event = []
                    if len(all_messages_from_graph_state) > count_history_ui_before_stream:
                        new_agent_messages_from_event = all_messages_from_graph_state[
                            count_history_ui_before_stream:]

                    if new_agent_messages_from_event:
                        st.session_state.messages.extend(
                            new_agent_messages_from_event)
                        st.session_state.current_turn_messages.extend(
                            new_agent_messages_from_event)
                        count_history_ui_before_stream = len(
                            st.session_state.messages)  # Update count

                        # Re-render seluruh konten giliran asisten saat ini
                        with assistant_turn_placeholder.container():
                            for i, msg_in_turn in enumerate(st.session_state.current_turn_messages):
                                is_final_animated = (
                                    (i == len(st.session_state.current_turn_messages) - 1) and
                                    isinstance(msg_in_turn, AIMessage) and
                                    not getattr(msg_in_turn, 'tool_calls', [])
                                )
                                _render_message_content(
                                    msg_in_turn, st, is_streaming_final_output=is_final_animated, is_production=True)  # is_production=True

            except Exception as e:
                st.error(f"Terjadi error saat menjalankan agent graph: {e}")
                print(f"❌ Error during graph execution: {e}")
                error_ai_msg = AIMessage(
                    content=f"Maaf, terjadi kesalahan teknis: {str(e)}")
                st.session_state.messages.append(error_ai_msg)
                st.session_state.current_turn_messages.append(error_ai_msg)
                # Re-render dengan pesan error
                with assistant_turn_placeholder.container():
                    _render_message_content(
                        error_ai_msg, st, is_streaming_final_output=True, is_production=True)  # is_production=True

            finally:
                # Apapun yang terjadi, selesaikan giliran pemrosesan
                # Pastikan masih dalam mode proses
                if st.session_state.get("processing_turn", False):
                    st.session_state.processing_turn = False
                    # Kosongkan untuk giliran berikutnya
                    st.session_state.current_turn_messages = []
                    st.rerun()  # Rerun untuk mengaktifkan kembali input & membersihkan UI


def app() -> None:
    """
    Fungsi utama untuk menjalankan aplikasi Streamlit Integrated ICONNET Assistant.
    """
    st.title("🤖 ICONNET Assistant")

    # Load custom CSS
    load_custom_css(os.path.join("static", "css", "style.css"))

    # Cek database pool
    db_pool = st.session_state.get("db")
    if not db_pool:
        st.error(
            "Koneksi Database Pool tidak tersedia. Fitur RAG dan SQL tidak akan berfungsi.")

    # Build atau load agent graph (gunakan cache resource)
    @st.cache_resource
    def get_graph():
        return build_graph()

    try:
        graph = get_graph()
        if graph is None:
            st.error(
                "Gagal membangun atau memuat agent graph. Chatbot tidak dapat berfungsi.")
            st.stop()
    except Exception as e:
        st.error(f"Terjadi error saat build/load graph: {str(e)}")
        st.stop()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"streamlit_chat_{st.session_state.get('useremail', 'anonymous')}_{int(time.time())}"
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    initialize_messages()
    display_all_messages_history()  # Tampilkan semua histori pesan
    process_user_input(graph, config)
