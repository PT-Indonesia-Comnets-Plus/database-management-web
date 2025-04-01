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

warnings.filterwarnings('ignore')

# Class untuk mendapatkan dokumen yang relevan dari PostgreSQL


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

    finally:
        cur.close()
        conn.close()

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


def app():
    st.title("Chatbot Berbasis Dokumen")
    if os.path.exists("style.css"):
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    qa_chain = create_qa_chain()
    if not qa_chain:
        return
    # Menyimpan pesan dalam session_state
    if 'message' not in st.session_state:
        st.session_state.message = []

    # Menampilkan pesan sebelumnya
    for message in st.session_state.message:
        st.chat_message(message["role"]).markdown(message["content"])

    # Input dari user
    prompt = st.chat_input("Masukkan pertanyaan:")
    if prompt:
        st.chat_message("user").markdown(prompt)
        st.session_state.message.append({"role": "user", "content": prompt})

        response = qa_chain.invoke({"query": prompt})
        assistant_message = response["result"]

        # Menampilkan jawaban dari chatbot
        st.chat_message("assistant").markdown(assistant_message)
        st.session_state.message.append(
            {"role": "assistant", "content": assistant_message})


if __name__ == "__main__":
    app()
