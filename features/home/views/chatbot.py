import streamlit as st
import warnings
import os
import time

# Import graph builder dan konfigurasi
from core.services.agent_graph.build_graph import build_graph
from core.services.agent_graph.load_config import TOOLS_CFG

from static.load_css import load_custom_css

warnings.filterwarnings('ignore')


def load_custom_css(path: str) -> None:
    """
    Memuat custom CSS dari file yang ditentukan.

    Args:
        path (str): Path ke file CSS.
    """
    if os.path.exists(path):
        try:
            with open(path) as f:
                st.markdown(f"<style>{f.read()}</style>",
                            unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Gagal memuat CSS: {e}")


def display_previous_messages() -> None:
    """
    Menampilkan semua pesan yang tersimpan di session_state.
    """
    if "messages" not in st.session_state or not isinstance(st.session_state.messages, list):
        st.session_state.messages = []

    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            st.chat_message("user").markdown(
                f"**{content}**", unsafe_allow_html=True)
        elif role == "assistant":
            st.chat_message("assistant").markdown(
                content, unsafe_allow_html=True)


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


def initialize_messages() -> None:
    """
    Inisialisasi riwayat pesan dalam session_state jika belum ada.
    """
    if "messages" not in st.session_state or not isinstance(st.session_state.messages, list):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Halo! Ada yang bisa saya bantu terkait aset atau dokumen ICONNET?"
        })


def process_user_input(graph, config) -> None:
    """
    Memproses input dari pengguna, mengirimkan ke agent graph, 
    lalu menampilkan respons dengan animasi.

    Args:
        graph: Graph agent untuk memproses pesan.
        config (dict): Konfigurasi untuk stream graph.
    """
    prompt = st.chat_input(
        "Tanyakan tentang aset, dokumen, atau informasi umum...")

    if prompt:
        st.chat_message("user").markdown(f"{prompt}", unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            thinking_placeholder.markdown("🤔 Memproses...")

            assistant_response_content = ""

            try:
                events = graph.stream(
                    {"messages": [("user", prompt)]},
                    config,
                    stream_mode="values"
                )

                final_state = None
                for event in events:
                    messages_in_event = event.get("messages", [])
                    if messages_in_event:
                        last_message = messages_in_event[-1]
                        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                            tool_names = [tc['name']
                                          for tc in last_message.tool_calls]
                            thinking_placeholder.markdown(
                                f"⚙️ Menggunakan tool: {', '.join(tool_names)}...")
                        final_state = event

                if final_state and final_state.get("messages"):
                    assistant_response_message = final_state["messages"][-1]
                    if assistant_response_message.type == 'ai':
                        assistant_response_content = assistant_response_message.content
                    else:
                        assistant_response_content = "Maaf, terjadi sedikit kebingungan saat memproses. Bisa coba lagi?"
                        print(
                            f"⚠️ Pesan terakhir dari graph bukan AI: {assistant_response_message}")
                else:
                    assistant_response_content = "Maaf, saya tidak dapat menghasilkan respons saat ini."
                    print(
                        "⚠️ Tidak ada state final atau pesan di state final dari graph stream.")

            except Exception as e:
                st.error(f"Terjadi error saat menjalankan agent graph: {e}")
                print(f"❌ Error during graph execution: {e}")
                assistant_response_content = "Maaf, terjadi kesalahan teknis saat memproses permintaan Anda."

            display_message_with_typing_animation(
                thinking_placeholder, assistant_response_content)

            st.session_state.messages.append({
                "role": "assistant",
                "content": assistant_response_content
            })


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

    # Build atau load agent graph
    try:
        graph = build_graph()
        if graph is None:
            st.error(
                "Gagal membangun atau memuat agent graph. Chatbot tidak dapat berfungsi.")
            st.stop()
    except Exception as e:
        st.error(f"Terjadi error saat build/load graph: {e}")
        st.stop()

    config = {"configurable": {"thread_id": TOOLS_CFG.thread_id}}

    initialize_messages()
    display_previous_messages()
    process_user_input(graph, config)


if __name__ == "__main__":
    app()
