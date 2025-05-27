# c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\tool_airflow_trigger.py
import streamlit as st
import time
import json
import requests  # Untuk berinteraksi dengan Airflow API
from typing import Dict, Optional
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

# Konfigurasi Airflow API (sebaiknya disimpan di st.secrets atau config file)
# Anda mungkin perlu mengaktifkan Basic Auth atau metode autentikasi lain di Airflow
AIRFLOW_BASE_URL = st.secrets.get("airflow", {}).get(
    "base_url", "http://localhost:8080")  # Contoh: http://your-airflow-webserver:8080
AIRFLOW_USERNAME = st.secrets.get("airflow", {}).get("username", "airflow")
AIRFLOW_PASSWORD = st.secrets.get("airflow", {}).get("password", "airflow")

# Pastikan ini adalah ID DAG yang benar dan task ID serta key XCom yang mengirimkan hasil
# DAG ID yang sudah dikonfirmasi ada di Airflow
ETL_DAG_ID = "iconnet_data_pipeline"
# Ganti dengan task_id yang mengirim XCom di DAG Anda (misalnya, 'load_and_report')
XCOM_TASK_ID = "load_and_report"
XCOM_KEY = "new_data_count"


def _get_airflow_token(retry_count=0, max_retries=2):
    """Get JWT token for Airflow API authentication with retry logic."""
    token_url = f"{AIRFLOW_BASE_URL}/auth/token"
    payload = {
        "username": AIRFLOW_USERNAME,
        "password": AIRFLOW_PASSWORD
    }

    logger.info(
        f"Requesting JWT token from: {token_url} (attempt {retry_count + 1}/{max_retries + 1})")
    logger.info(f"Using username: {AIRFLOW_USERNAME}")

    try:
        response = requests.post(token_url, json=payload, timeout=15)
        logger.info(f"Token request response status: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                logger.info(
                    f"JWT token obtained successfully (length: {len(access_token)})")
                # Log first 20 chars for debugging (safe portion)
                logger.debug(f"Token starts with: {access_token[:20]}...")
                return access_token
            else:
                logger.error("No access_token in response")
                logger.error(f"Token response data: {token_data}")

        # If we get here, the response was not successful
        logger.error(
            f"Token request failed with status {response.status_code}")
        logger.error(f"Response text: {response.text}")

        # Retry logic for certain errors
        if retry_count < max_retries and response.status_code in [500, 502, 503, 504]:
            logger.info(
                f"Retrying token request due to server error (attempt {retry_count + 1})")
            import time
            time.sleep(2)  # Wait 2 seconds before retry
            return _get_airflow_token(retry_count + 1, max_retries)

        return None

    except requests.exceptions.RequestException as req_err:
        logger.error(f"Request exception getting Airflow token: {req_err}")

        # Retry for network-related errors
        if retry_count < max_retries:
            logger.info(
                f"Retrying token request due to network error (attempt {retry_count + 1})")
            import time
            time.sleep(2)
            return _get_airflow_token(retry_count + 1, max_retries)

        return None
    except Exception as e:
        logger.error(f"Unexpected error getting Airflow token: {e}")
        return None


def _make_airflow_api_request(method: str, endpoint: str, payload: Optional[Dict] = None) -> Optional[Dict]:
    """Helper untuk membuat request ke Airflow API dengan JWT authentication."""
    logger.info(f"Making Airflow API request: {method} {endpoint}")

    # Get JWT token
    token = _get_airflow_token()
    if not token:
        logger.error(
            "Cannot proceed with API request - no JWT token available")
        return {"error": "Failed to authenticate with Airflow - could not get JWT token"}

    logger.info("JWT token obtained for API request")

    url = f"{AIRFLOW_BASE_URL}/api/v2/{endpoint.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    logger.info(f"Airflow API Request: {method} {url}")
    logger.debug(
        f"Headers (auth redacted): {{'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer [REDACTED]'}}")
    logger.debug(f"Payload: {payload}")

    try:
        if method.upper() == "POST":
            response = requests.post(
                url, headers=headers, json=payload, timeout=30)
        elif method.upper() == "GET":
            response = requests.get(
                url, headers=headers, timeout=30)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return {"error": f"Unsupported HTTP method: {method}"}

        logger.info(f"Response status: {response.status_code}")

        if response.status_code == 401:
            logger.error(
                "401 Unauthorized - JWT token may be invalid or expired")
            logger.error(f"Response headers: {dict(response.headers)}")
            logger.error(f"Response body: {response.text}")

        response.raise_for_status()  # Raise HTTPError untuk status 4xx/5xx
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        error_content = "No additional details."
        try:
            error_content = response.json()
        except json.JSONDecodeError:
            error_content = response.text
        logger.error(
            f"Airflow API HTTP error: {http_err} - Status: {response.status_code if 'response' in locals() else 'N/A'} - Details: {error_content}")
        return {"error": f"Airflow API HTTP error: {http_err}", "status_code": response.status_code if 'response' in locals() else 'N/A', "details": error_content}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Airflow API request error: {req_err}")
        return {"error": f"Airflow API request error: {req_err}"}
    except json.JSONDecodeError:
        response_text = response.text if 'response' in locals() else 'N/A'
        logger.error(
            f"Failed to decode JSON response from Airflow API. Response text: {response_text}")
        return {"error": "Failed to decode JSON response from Airflow API."}


@tool
def trigger_spreadsheet_etl_and_get_summary() -> str:
    """
    Memicu pipeline ETL dan mengembalikan ringkasan. Utamanya untuk data spreadsheet,
    tetapi juga merupakan tool utama untuk menjalankan permintaan ETL pipeline secara umum.

    Fungsi utama:
    - Menjalankan pipeline ETL yang dikonfigurasi di Airflow.
    - Memproses data (seringkali dari spreadsheet, tapi bisa juga sumber lain jika pipeline dikonfigurasi demikian).
    - Mengembalikan ringkasan hasil, seperti jumlah data baru yang diproses.

    GUNAKAN TOOL INI KETIKA USER MEMINTA:
    ✅ Untuk "menjalankan ETL pipeline saya" atau "run my ETL pipeline".
    ✅ Untuk "menjalankan ETL" atau "run ETL".
    ✅ Untuk memproses data dari spreadsheet ("process spreadsheet", "update from excel").
    ✅ Untuk mendapatkan ringkasan data baru dari spreadsheet ("new data from sheet").
    ✅ Query umum terkait "ETL", "data pipeline" yang perlu dijalankan.

    JANGAN GUNAKAN UNTUK:
    ❌ Query data yang sudah ada di database (gunakan `query_asset_database`).
    ❌ Pencarian informasi umum (gunakan `search_internal_documents` atau `TavilySearchResults`).
    ❌ Pembuatan visualisasi secara langsung tanpa menjalankan ETL (gunakan `create_visualization` setelah data ada).

    Tool ini akan berinteraksi dengan Airflow untuk menjalankan DAG yang relevan.
    """
    logger.info(
        f"Running tool: trigger_spreadsheet_etl_and_get_summary for DAG '{ETL_DAG_ID}'")    # 1. Memicu DAG
    import datetime
    # Generate unique DAG run ID with timestamp
    dag_run_id = f"chatbot_trigger_{int(time.time())}"

    # Create logical_date in ISO format (required by Airflow API v2)
    logical_date = datetime.datetime.now(datetime.timezone.utc).isoformat()

    trigger_payload = {
        "dag_run_id": dag_run_id,
        "logical_date": logical_date,
        # Konfigurasi opsional
        "conf": {"source_trigger": "chatbot_request", "timestamp": time.time()}
    }
    trigger_response = _make_airflow_api_request(
        "POST", f"dags/{ETL_DAG_ID}/dagRuns", payload=trigger_payload)

    if not trigger_response or "error" in trigger_response:
        logger.error(
            f"Failed to trigger DAG '{ETL_DAG_ID}'. Response: {trigger_response}")
        error_msg = trigger_response.get('details', {}).get('detail', trigger_response.get(
            'error', 'Unknown error')) if trigger_response else "No response"        # Check if it's a connection or method error (Airflow not available)
        if trigger_response and trigger_response.get('status_code') == 401:
            error_msg = f"""🚫 **Authentication Error**: Pipeline ETL Airflow tidak dapat diakses karena masalah autentikasi (HTTP 401 - Unauthorized).

**Troubleshooting Steps:**
1. ✅ Username/Password: Pastikan username dan password Airflow benar di konfigurasi `.streamlit/secrets.toml`
2. ✅ Default Credentials: Username dan password default biasanya 'airflow'/'airflow' 
3. ✅ Airflow Running: Pastikan Airflow berjalan di {AIRFLOW_BASE_URL}
4. ✅ API Access: Coba akses {AIRFLOW_BASE_URL} di browser untuk memastikan Airflow aktif

**Current Config:**
- URL: {AIRFLOW_BASE_URL}
- Username: {AIRFLOW_USERNAME}

Silakan periksa konfigurasi dan coba lagi."""
            return json.dumps({"status": "airflow_auth_error", "message": error_msg})
        elif trigger_response and trigger_response.get('status_code') == 405:
            error_msg = f"Pipeline ETL Airflow tidak tersedia saat ini (HTTP 405 - Method Not Allowed). Ini bisa terjadi jika Airflow server tidak berjalan atau konfigurasi API berbeda. Silakan coba lagi nanti atau hubungi administrator."
            return json.dumps({"status": "airflow_api_error", "message": error_msg})
        elif trigger_response and 'Connection' in str(trigger_response.get('error', '')):
            error_msg = "Pipeline ETL Airflow tidak dapat diakses saat ini (koneksi gagal). Pastikan Airflow server berjalan di http://localhost:8080 atau hubungi administrator."
            # Berikan pesan yang lebih spesifik
            return json.dumps({"status": "airflow_connection_error", "message": error_msg})
        return json.dumps({"status": "airflow_error", "message": f"Gagal memicu pipeline ETL di Airflow. Detail: {error_msg}. Pastikan Airflow berjalan dan konfigurasi benar."})

    dag_run_id = trigger_response.get("dag_run_id")
    if not dag_run_id:
        logger.error(
            f"DAG '{ETL_DAG_ID}' triggered, but no DAG Run ID received. Response: {trigger_response}")
        return json.dumps({"status": "dag_trigger_error", "message": f"Pipeline ETL berhasil dipicu, tetapi tidak mendapatkan DAG Run ID. Respons: {trigger_response}"})
    logger.info(
        f"DAG '{ETL_DAG_ID}' triggered successfully. DAG Run ID: {dag_run_id}")

    # 2. Memantau status DAG Run (dengan timeout)
    max_wait_time_seconds = 300  # Tunggu maksimal 5 menit
    check_interval_seconds = 15
    start_time = time.time()

    while time.time() - start_time < max_wait_time_seconds:
        status_response = _make_airflow_api_request(
            "GET", f"dags/{ETL_DAG_ID}/dagRuns/{dag_run_id}")
        if not status_response or "error" in status_response:
            logger.error(
                f"Failed to get status for DAG run '{dag_run_id}'. Response: {status_response}")
            error_msg = status_response.get('details', {}).get('detail', status_response.get(
                'error', 'Unknown error')) if status_response else "No response"
            return json.dumps({"status": "dag_status_error", "message": f"Gagal mendapatkan status DAG run '{dag_run_id}'. Detail: {error_msg}."})

        current_state = status_response.get("state")
        logger.info(f"Status for DAG Run '{dag_run_id}': {current_state}")

        if current_state == "success":
            logger.info(
                f"DAG Run '{dag_run_id}' completed successfully. Attempting to retrieve XCom.")
            # 3. (PENTING) Mengambil hasil dari XComs
            xcom_endpoint = f"dags/{ETL_DAG_ID}/dagRuns/{dag_run_id}/taskInstances/{XCOM_TASK_ID}/xcomEntries/{XCOM_KEY}"
            logger.debug(
                f"Attempting to get XCom from endpoint: {xcom_endpoint}")
            xcom_response = _make_airflow_api_request("GET", xcom_endpoint)

            if xcom_response and "value" in xcom_response:
                raw_xcom_value = xcom_response["value"]
                logger.info(
                    f"Raw XCom value received for '{XCOM_KEY}' from task '{XCOM_TASK_ID}': {raw_xcom_value}")
                try:
                    # Jika XCom adalah integer yang dikirim dari PythonOperator,
                    # nilainya biasanya berupa string dari integer tersebut.
                    new_data_count = int(raw_xcom_value)
                    logger.info(
                        f"Successfully parsed XCom value to int: {new_data_count}")                    # json.JSONDecodeError tidak relevan jika langsung int()
                    return json.dumps({"status": "success", "message": f"Pipeline ETL berhasil dijalankan. Jumlah data baru yang berhasil dimuat: {new_data_count}."})
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Error parsing XCom value '{raw_xcom_value}' as int: {e}. Full XCom response: {xcom_response}")
                    return json.dumps({"status": "xcom_parse_error", "message": f"Pipeline ETL berhasil, tetapi gagal memproses jumlah data baru dari XComs. Nilai mentah XCom: {str(raw_xcom_value)[:200]}. Error: {e}"})
            else:
                logger.warning(
                    f"Failed to retrieve XCom key '{XCOM_KEY}' from task '{XCOM_TASK_ID}'. Response: {xcom_response}")
                error_detail = xcom_response.get('details', {}).get(
                    'detail', xcom_response.get('error', '')) if xcom_response else 'No response'
                return json.dumps({"status": "xcom_retrieve_error", "message": f"Pipeline ETL berhasil, tetapi tidak dapat mengambil ringkasan jumlah data baru. Pastikan task '{XCOM_TASK_ID}' mengirimkan XCom dengan key '{XCOM_KEY}'. Detail dari Airflow: {error_detail}"})

        elif current_state in ["failed", "upstream_failed", "skipped", "removed", "queued"]:
            logger.warning(
                f"DAG Run '{dag_run_id}' finished with non-success state: {current_state}")
            return json.dumps({"status": "dag_failed", "message": f"Pipeline ETL '{ETL_DAG_ID}' di Airflow selesai dengan status: {current_state}. Tidak ada data baru yang dapat dilaporkan."})

        time.sleep(check_interval_seconds)

    logger.warning(
        f"Timeout waiting for DAG Run '{dag_run_id}' to complete after {max_wait_time_seconds // 60} minutes.")
    return json.dumps({"status": "timeout", "message": f"Pipeline ETL '{ETL_DAG_ID}' masih berjalan di Airflow setelah {max_wait_time_seconds // 60} menit atau gagal merespons. Silakan periksa statusnya langsung di Airflow."})
