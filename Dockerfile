# Gunakan base image Python yang sesuai dengan versi di pyproject.toml
# 'requires-python = ">=3.11"'
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app

# Install Poetry
# Sebaiknya pin versi Poetry untuk build yang konsisten
ENV POETRY_VERSION=1.8.3
RUN pip install "poetry==${POETRY_VERSION}"

# Nonaktifkan pembuatan virtual environment oleh Poetry di dalam container,
# karena container itu sendiri sudah merupakan lingkungan terisolasi.
RUN poetry config virtualenvs.create false

# Salin file dependensi terlebih dahulu untuk memanfaatkan Docker layer caching
# Jika file-file ini tidak berubah, Docker tidak perlu menginstal ulang dependensi
COPY pyproject.toml poetry.lock* /app/

# Install dependensi proyek (hanya dependensi produksi, tanpa dev dependencies)
# --no-interaction: Jangan ajukan pertanyaan interaktif
# --no-ansi: Nonaktifkan output ANSI untuk log yang lebih bersih
RUN poetry install --no-dev --no-interaction --no-ansi

# Salin sisa kode aplikasi ke dalam working directory di container
COPY . /app/

# Port default yang digunakan Streamlit
EXPOSE 8501

# Perintah untuk menjalankan aplikasi Streamlit Anda
# Ganti 'your_streamlit_app_file.py' dengan nama file Python utama aplikasi Streamlit Anda
# Misalnya, jika file utama Anda adalah main.py, gunakan "streamlit", "run", "main.py"
CMD ["streamlit", "run", "your_streamlit_app_file.py", "--server.port=8501", "--server.address=0.0.0.0"]
