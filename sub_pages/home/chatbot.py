import streamlit as st
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.schema import BaseRetriever
from utils.database import connect_db
import warnings
from typing import List
import os
import time

warnings.filterwarnings('ignore')

# Class untuk mendapatkan dokumen yang relevan dari PostgreSQL

api_key = os.getenv("GOOGLE_API_KEY", st.secrets["google"]["api_key"])


class PostgresRetriever(BaseRetriever):
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Cari dokumen relevan dari PostgreSQL berdasarkan query."""
        results = search_similar_documents(query)  # Panggil fungsi pencarian
        return [Document(page_content=row[1], metadata=row[2]) for row in results]

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """Versi async dari pencarian dokumen."""
        return self.get_relevant_documents(query)

# Fungsi pencarian di database PostgreSQL


def search_similar_documents(query: str):
    """
    Mencari dokumen yang relevan di PostgreSQL berdasarkan embedding query.
    """
    try:
        conn = connect_db()  # Koneksi ke database
        cur = conn.cursor()

        # Inisialisasi model embedding Google untuk query embedding
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        query_embedding = embeddings.embed_query(query)

        # Query SQL untuk pencarian dokumen relevan
        cur.execute(
            """
            SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT 5;
            """,
            (query_embedding, query_embedding)
        )

        results = cur.fetchall()  # Ambil hasil pencarian
        return results

    except Exception as e:
        print(f"❌ Error saat mencari dokumen: {e}")
        return []


# Fungsi untuk membuat QA Chain


def create_qa_chain() -> RetrievalQA:
    """
    Membuat QA Chain menggunakan LLM dan PostgresRetriever.
    """
    try:
        # Inisialisasi model AI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=1,
            api_key=api_key,
            convert_system_message_to_human=True,
            system_message="Jawab berdasarkan dokumen yang tersedia.",
            model_kwargs={"max_output_tokens": 8192,
                          "top_k": 10, "top_p": 0.95}
        )

        # Gunakan retriever berbasis PostgreSQL
        retriever = PostgresRetriever()

        # Bangun QA Chain
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )

    except Exception as e:
        print(f"❌ Error creating QA chain: {e}")
        return None


def display_previous_messages():
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.chat_message("user").markdown(
                f"**{message['content']}**", unsafe_allow_html=True)
        elif message["role"] == "assistant":
            st.chat_message("assistant").markdown(
                message["content"], unsafe_allow_html=True)


# Fungsi untuk menampilkan animasi bertahap
def display_message_with_typing_animation(placeholder, message, typing_speed=0.1):
    displayed_message = ""
    for char in message:
        displayed_message += char
        time.sleep(0.02)  # Memberikan jeda waktu 20ms untuk setiap karakter
        placeholder.markdown(displayed_message)


def app():
    st.title("🤖 **Chatbot Berbasis Dokumen**")

    if os.path.exists("static\css\style.css"):
        with open("static\css\style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Placeholder untuk chatbot
    qa_chain = create_qa_chain()
    if not qa_chain:
        st.error("Gagal membuat QA chain.")
        return

    # Menyimpan pesan dalam session_state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Menampilkan pesan sebelumnya
    display_previous_messages()

    # Input dari user
    prompt = st.chat_input("Masukkan pertanyaan Anda di sini...")
    if prompt:
        # Tampilkan pesan user di UI
        st.chat_message("user").markdown(
            f"**{prompt}**", unsafe_allow_html=True)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Animasi "thinking" sebelum respons assistant
        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            for dot_count in range(3):
                thinking_placeholder.markdown(f"🤔 Thinking{'.' * dot_count}")
                time.sleep(1)

            # Mendapatkan respons dari model
            response = qa_chain.invoke({"query": prompt})
            assistant_message = response["result"]

            # Tampilkan animasi bertahap untuk respons assistant
            display_message_with_typing_animation(
                thinking_placeholder, assistant_message)

        # Simpan respons assistant
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message})


if __name__ == "__main__":
    app()
