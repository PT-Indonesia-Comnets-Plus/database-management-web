import streamlit as st
import google.generativeai as genai
import re
import psycopg2

# Fungsi ambil skema data


def get_schema(db):

    conn = None
    try:
        conn = db.getconn()
        with conn.cursor() as cur:
            cur.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name IN (
                'user_terminals', 'clusters', 'home_connecteds',
                'dokumentasis', 'additional_informations', 'pelanggans'
            )
            ORDER BY table_name, ordinal_position;
            """)
            rows = cur.fetchall()

        schema = {}
        for table, column, dtype in rows:
            schema.setdefault(table, []).append(f"{column} ({dtype})")
        return schema

    except (psycopg2.OperationalError, psycopg2.pool.PoolError) as pool_err:
        st.error(
            f"Error koneksi/pool database saat mengambil skema: {pool_err}")
        return None
    except Exception as e:
        st.error(f"Gagal mengambil skema: {e}")
        return None
    finally:
        if conn:
            db.putconn(conn)

# Fungsi generate SQL dari Gemini


def generate_sql_query(schema, user_question):
    if not schema:
        return None
    model = genai.GenerativeModel("gemini-2.0-flash")
    schema_str = "\n".join(
        f"Tabel {t}:\n" + "\n".join([f" - {c}" for c in cs]) for t, cs in schema.items())
    max_schema_length = 5000
    schema_str = schema_str[:max_schema_length] + \
        "...\n(dipangkas)" if len(
            schema_str) > max_schema_length else schema_str
    prompt = f"""
    Buat query SQL PostgreSQL berdasarkan skema dan pertanyaan berikut.
    Jika ada perbandingan string (seperti nama kota), pastikan gunakan fungsi LOWER() agar pencarian tidak sensitif terhadap huruf besar/kecil.
    Tampilkan query saja tanpa ``` atau penjelasan.

    Skema:
    {schema_str}

    Pertanyaan:
    {user_question}

    Query:
    """
    try:
        response = model.generate_content(prompt)
        return re.sub(r"```sql\s*|\s*```", "", response.text.strip(), flags=re.IGNORECASE)
    except Exception as e:
        st.error(f"Error Gemini: {e}")
        return None


def execute_query(query, db):

    conn = None
    try:
        conn = db.getconn()
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description:  # Jika query menghasilkan kolom (SELECT)
                data = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
            else:
                conn.commit()
                data = f"Berhasil. Baris terpengaruh: {cur.rowcount}"
                columns = []
        return data, columns

    except (psycopg2.OperationalError, psycopg2.pool.PoolError) as pool_err:
        st.error(
            f"Error koneksi/pool database saat eksekusi query: {pool_err}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return None, f"Error Koneksi/Pool: {pool_err}"
    except Exception as e:
        st.error(f"Error saat eksekusi query: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return None, f"Error Eksekusi: {e}"
    finally:
        if conn:
            db.putconn(conn)

# Jawaban natural dari hasil


def generate_natural_answer(question, results, colnames):
    if isinstance(results, str):
        return results
    if not results:
        return "Tidak ada data ditemukan."

    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        table_str = f"Kolom: {' | '.join(colnames)}\nData:\n" + \
            "\n".join([" | ".join(map(str, row)) for row in results])
        if len(table_str) > 5000:
            table_str = table_str[:5000] + "\n...(dipotong)"
        prompt = f"""
Anda adalah asisten AI yang cerdas dan komunikatif. Tugas Anda adalah membantu menjelaskan hasil query SQL dari database ke dalam bahasa Indonesia yang alami, sopan, dan mudah dimengerti oleh pengguna awam.

Ikuti pedoman ini saat memberikan jawaban:
- Gunakan gaya penulisan seperti penjelasan manusia profesional kepada rekan kerja yang tidak terlalu teknis.
- Sajikan informasi secara ringkas, jelas, dan runtut.
- Jika hasil berupa data numerik, berikan insight atau pola yang terlihat.
- Jika hasilnya kosong, beri tahu bahwa data tidak ditemukan dengan nada sopan.
- Hindari menyebut "query" atau "SQL", cukup jelaskan hasilnya saja.
- Jika data terlalu panjang, berikan ringkasan umum, bukan daftar data satu per satu.

Berikut adalah pertanyaan dari pengguna dan hasil yang diperoleh dari database:

Pertanyaan Pengguna:
{question}

Data yang Ditemukan:
{table_str}

Tolong berikan penjelasan dalam bahasa Indonesia yang ringkas dan alami berdasarkan data di atas:
"""
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        return f"Gagal merangkum: {e}"

# Streamlit App


def app():
    st.title("SQL Chatbot: Gemini x Supabase")
    db = st.session_state.get("db")
    if not db:
        st.error("Connection Pool tidak tersedia.")
    question = st.text_input("Tanyakan sesuatu tentang data aset:")
    if st.button("Kirim Pertanyaan"):
        with st.spinner("Memproses..."):
            schema = get_schema(st.session_state.db)
            query = generate_sql_query(schema, question)
            if not query:
                st.error("Gagal membuat query.")
                return

            results, info = execute_query(query, st.session_state.db)
            if isinstance(info, str):
                st.error(info)
                return

            answer = generate_natural_answer(question, results, info)
            st.markdown("### Jawaban:")
            st.write(answer)
            with st.expander("Lihat Query SQL"):
                st.code(query, language="sql")


if __name__ == "__main__":
    app()
