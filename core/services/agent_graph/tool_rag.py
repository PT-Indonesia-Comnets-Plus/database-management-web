import streamlit as st
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.schema import BaseRetriever
from typing import List
import os
import psycopg2
import json


class PostgresRetriever(BaseRetriever):
    """Retriever yang mencari dokumen relevan dari database PostgreSQL."""

    def get_relevant_documents(self, query: str) -> List[Document]:
        try:
            results = search_similar_documents(query, db=st.session_state.db)
            documents = [
                Document(page_content=row[1], metadata=json.loads(row[2])) for row in results]
            if not documents:
                st.warning("Tidak ditemukan dokumen relevan untuk query ini.")
            return documents
        except Exception as e:
            st.error(f"Error saat mengambil dokumen relevan: {str(e)}")
            return []

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return self.get_relevant_documents(query)


def search_similar_documents(query: str, db):
    """Cari dokumen yang relevan di PostgreSQL berdasarkan embedding query."""
    conn = None
    try:
        conn = db.getconn()
        with conn.cursor() as cur:
            embeddings = GoogleGenerativeAIEmbeddings(
                model=TOOLS_CFG.policy_rag_embedding_model)
            query_embedding = embeddings.embed_query(query)

            cur.execute(
                """
                SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity
                FROM documents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 5;
                """,
                (query_embedding, query_embedding)
            )

            return cur.fetchall()
    except (psycopg2.OperationalError, psycopg2.pool.PoolError) as pool_err:
        st.error(f"❌ Error koneksi database: {pool_err}")
    except Exception as e:
        st.error(f"❌ Error saat mencari dokumen: {e}")
    finally:
        if conn:
            db.putconn(conn)
    return []


# Fungsi untuk membuat QA Chain


def create_qa_chain() -> RetrievalQA:
    """Membuat QA Chain dengan settingan advanced untuk backoffice telekomunikasi."""
    try:
        llm = ChatGoogleGenerativeAI(
            model=TOOLS_CFG.policy_rag_llm,  # Model lebih kuat
            api_key=os.getenv("GOOGLE_API_KEY",
                              st.secrets["google"]["api_key"]),
            temperature=TOOLS_CFG.policy_rag_llm_temperature,  # Konsisten, tidak ngawur
            convert_system_message_to_human=True,
            system_message=(
                "Kamu adalah asisten cerdas untuk tim backoffice perusahaan telekomunikasi. "
                "Jawablah hanya berdasarkan dokumen yang tersedia. "
                "Jika jawaban tidak ada, katakan dengan sopan 'Maaf, informasi tersebut tidak tersedia dalam data kami.' "
                "Jawaban harus singkat, padat, dan teknis."
            ),
            model_kwargs={
                "max_output_tokens": 4096,
                "top_p": 0.9,
                "top_k": 10,
            }
        )

        retriever = PostgresRetriever()

        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
    except Exception as e:
        st.error(f"❌ Gagal membuat QA Chain: {e}")


def handle_prompt_response(prompt, qa_chain):
    try:
        response = qa_chain.invoke({"query": prompt})
        assistant_message = response.get("result", "").strip()

        if not assistant_message:
            assistant_message = "Maaf, saya tidak menemukan jawaban berdasarkan dokumen yang tersedia."

        return assistant_message
    except Exception as e:
        st.error(f"❌ Terjadi error saat memproses permintaan Anda: {e}")
        return "Terjadi kesalahan teknis. Silakan coba lagi nanti."
