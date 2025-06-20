# Gunakan image dasar Python
FROM python:3.11-slim-buster

# Atur direktori kerja di dalam container
WORKDIR /app

RUN pip install uv

COPY requirements.txt .

RUN uv pip install --system -r requirements.txt

COPY . .

# Paparkan port yang digunakan Streamlit (defaultnya 8501)
EXPOSE 8501

CMD ["streamlit", "run", "Main_Page.py", "--server.port", "8501", "--server.address", "0.0.0.0"]