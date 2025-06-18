import streamlit as st
import time
import json
import requests
from typing import Dict, Optional
from langchain_core.tools import tool
import logging
from ....utils.load_config import TOOLS_CFG

logger = logging.getLogger(__name__)

AIRFLOW_BASE_URL = TOOLS_CFG.airflow_url
AIRFLOW_USERNAME = TOOLS_CFG.airflow_username
AIRFLOW_PASSWORD = TOOLS_CFG.airflow_password

# DAG dan task configuration
ETL_DAG_ID = "iconnet_data_pipeline"
XCOM_TASK_ID = "load"
XCOM_KEY = "new_data_count"

# Cache untuk JWT token
_jwt_token_cache = {"token": None, "expires_at": 0}


def _get_jwt_token() -> Optional[str]:
    """Mendapatkan JWT token dari Airflow untuk Bearer authentication."""
    current_time = time.time()

    # Gunakan cached token jika masih valid (dengan margin 60 detik)
    if _jwt_token_cache["token"] and current_time < (_jwt_token_cache["expires_at"] - 60):
        logger.info("Using cached JWT token")
        return _jwt_token_cache["token"]

    logger.info("Getting new JWT token from Airflow")

    # Endpoint untuk mendapatkan JWT token di Airflow 3.0
    token_url = f"{AIRFLOW_BASE_URL}/auth/token"

    payload = {
        "username": AIRFLOW_USERNAME,
        "password": AIRFLOW_PASSWORD
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(
            token_url, json=payload, headers=headers, timeout=30)

        logger.info(f"Token request status: {response.status_code}")

        # Accept both 200 and 201 status codes
        if response.status_code in [200, 201]:
            token_data = response.json()
            token = token_data.get("access_token")

            if token:
                # Cache token dengan expiry time (biasanya 1 jam, kita set 50 menit untuk safety)
                _jwt_token_cache["token"] = token
                _jwt_token_cache["expires_at"] = current_time + \
                    (50 * 60)  # 50 minutes
                logger.info("Successfully obtained JWT token")
                return token
            else:
                logger.error("No access_token in response")
                return None
        else:
            logger.error(
                f"Failed to get JWT token: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting JWT token: {e}")
        return None


def _make_airflow_api_request(method: str, endpoint: str, payload: Optional[Dict] = None) -> Optional[Dict]:
    """Helper untuk membuat request ke Airflow API dengan Bearer token authentication."""
    logger.info(
        f"Making Airflow API request: {method} {endpoint}")    # Dapatkan JWT token
    token = _get_jwt_token()
    if not token:
        return {"error": "Failed to obtain JWT token for Airflow authentication"}

    url = f"{AIRFLOW_BASE_URL}/api/v2/{endpoint.lstrip('/')}"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    logger.info(f"Airflow API Request: {method} {url}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload: {payload}")

    try:
        if method.upper() == "POST":
            response = requests.post(
                url, headers=headers, json=payload, timeout=30)
        elif method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "PATCH":
            response = requests.patch(
                url, headers=headers, json=payload, timeout=30)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return {"error": f"Unsupported HTTP method: {method}"}

        logger.info(f"Response status: {response.status_code}")

        if response.status_code == 401:
            logger.error(
                "401 Unauthorized - JWT token may be invalid or expired")
            logger.error(f"Response headers: {dict(response.headers)}")
            logger.error(f"Response body: {response.text}")
            # Clear cached token untuk retry
            _jwt_token_cache["token"] = None
            _jwt_token_cache["expires_at"] = 0

        response.raise_for_status()
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


def _diagnose_airflow_connection() -> Dict:
    """Diagnostic function to test Airflow connection and provide detailed info"""
    diagnosis = {
        "airflow_server": "unknown",
        "authentication": "unknown",
        "api_version": "unknown",
        "dags_available": 0,
        "target_dag_exists": False,
        "recommendations": []
    }

    # Test JWT authentication first (which also tests server connectivity)
    token = _get_jwt_token()
    if token:
        diagnosis["authentication"] = "jwt_success"
        diagnosis["airflow_server"] = "reachable"
    else:
        diagnosis["authentication"] = "jwt_failed"
        diagnosis["airflow_server"] = "unreachable"
        diagnosis["recommendations"].append(
            "Check if Airflow server is running and accessible")
        diagnosis["recommendations"].append(
            "Check Airflow username/password credentials")    # Test API version and DAG availability
    if token:
        try:
            # Get Airflow version
            version_response = _make_airflow_api_request("GET", "version")
            if version_response and "version" in version_response:
                # List DAGs
                diagnosis["api_version"] = version_response["version"]
            dags_response = _make_airflow_api_request("GET", "dags")
            if dags_response and "dags" in dags_response:
                diagnosis["dags_available"] = len(dags_response["dags"])

            # Check for target DAG directly (more reliable than listing)
            target_dag_response = _make_airflow_api_request(
                "GET", f"dags/{ETL_DAG_ID}")
            if target_dag_response and "dag_id" in target_dag_response:
                diagnosis["target_dag_exists"] = True
                # Check DAG status
                if not target_dag_response.get("is_active", False):
                    diagnosis["recommendations"].append(
                        f"DAG '{ETL_DAG_ID}' found but not active - may need to be triggered first")
                if target_dag_response.get("is_paused", True):
                    diagnosis["recommendations"].append(
                        f"DAG '{ETL_DAG_ID}' is paused - will auto-unpause during execution")
            else:
                diagnosis["target_dag_exists"] = False
                diagnosis["recommendations"].append(
                    f"Deploy DAG '{ETL_DAG_ID}' to Airflow")

        except Exception as e:
            diagnosis["recommendations"].append(f"API test failed: {str(e)}")

    return diagnosis


def _trigger_dag(dag_id: str, conf: Optional[Dict] = None) -> Dict:
    """Trigger DAG dan return execution info."""
    logger.info(
        f"Attempting to trigger DAG: {dag_id}")    # Payload untuk trigger DAG with required logical_date
    from datetime import datetime

    trigger_payload = {
        "conf": conf or {},
        "dag_run_id": f"manual__{int(time.time())}",
        "logical_date": datetime.utcnow().isoformat() + "Z"
    }

    endpoint = f"dags/{dag_id}/dagRuns"
    result = _make_airflow_api_request("POST", endpoint, trigger_payload)

    if result and "error" not in result:
        logger.info(f"Successfully triggered DAG {dag_id}")
        return {
            "success": True,
            "dag_run_id": result.get("dag_run_id"),
            "execution_date": result.get("execution_date"),
            "state": result.get("state", "queued")
        }
    else:
        logger.error(f"Failed to trigger DAG {dag_id}: {result}")

        # Enhanced error reporting
        error_details = {
            "success": False,
            "error": result.get("error", "Unknown error"),
            "details": result
        }

        # Add HTTP status code if available
        if result and "status_code" in result:
            error_details["status_code"] = result["status_code"]

        return error_details


def _wait_for_dag_completion(dag_id: str, dag_run_id: str, max_wait_seconds: int = 300) -> Dict:
    """Wait for DAG completion dan return status."""
    logger.info(f"Waiting for DAG {dag_id} run {dag_run_id} to complete")

    start_time = time.time()
    check_interval = 10  # Check setiap 10 detik

    while (time.time() - start_time) < max_wait_seconds:
        # Get DAG run status
        endpoint = f"dags/{dag_id}/dagRuns/{dag_run_id}"
        status_result = _make_airflow_api_request("GET", endpoint)

        if status_result and "error" not in status_result:
            state = status_result.get("state")
            logger.info(f"DAG run state: {state}")

            if state in ["success", "failed"]:
                return {
                    "completed": True,
                    "state": state,
                    "end_date": status_result.get("end_date"),
                    "duration": status_result.get("duration")
                }
            elif state == "running":
                logger.info(
                    f"DAG still running, waiting {check_interval} seconds...")
                time.sleep(check_interval)
            else:
                logger.info(f"DAG state: {state}, continuing to wait...")
                time.sleep(check_interval)
        else:
            logger.error(f"Error checking DAG status: {status_result}")
            return {
                "completed": False,
                "error": "Failed to check DAG status",
                "details": status_result
            }

    # Timeout reached
    logger.warning(f"Timeout waiting for DAG {dag_id} to complete")
    return {
        "completed": False,
        "error": "Timeout waiting for DAG completion",
        "timeout_seconds": max_wait_seconds
    }


def _get_xcom_value(dag_id: str, dag_run_id: str, task_id: str, key: str) -> Optional[any]:
    """Retrieve XCom value from completed task."""
    logger.info(
        f"Getting XCom value: dag_id={dag_id}, task_id={task_id}, key={key}")

    endpoint = f"dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/xcomEntries/{key}"
    result = _make_airflow_api_request("GET", endpoint)

    if result and "error" not in result:
        logger.info(
            f"Successfully retrieved XCom value: {result.get('value')}")
        return result.get("value")
    else:
        # Check if this is a 404 (not found) vs other error
        if isinstance(result, dict) and result.get('status_code') == 404:
            logger.warning(
                f"XCom value not found (404): task '{task_id}' might not set key '{key}' or task didn't run")
        else:
            logger.error(f"Failed to get XCom value: {result}")
        return None


@tool
def trigger_spreadsheet_etl_and_get_summary(question: str = "") -> str:
    """
    Trigger proses ETL untuk update data spreadsheet dan mendapatkan ringkasan data baru.

    Tool ini akan:
    1. Menjalankan pipeline ETL di Airflow
    2. Menunggu hingga proses selesai
    3. Mengambil informasi tentang data baru yang berhasil diproses

    Args:
        question: Pertanyaan dari user terkait ETL atau data baru (opsional)

    Returns:
        str: Ringkasan hasil ETL termasuk jumlah data baru yang diproses
    """

    logger.info(f"ETL tool called with question: {question}")

    try:
        # Step 1: Diagnose connection
        logger.info("Step 1: Diagnosing Airflow connection...")
        diagnosis = _diagnose_airflow_connection()

        if diagnosis["authentication"] != "jwt_success":
            return f"❌ Gagal terhubung atau autentikasi ke Airflow: {diagnosis['authentication']}\n\nRekomendasi: {', '.join(diagnosis['recommendations'])}"

        if not diagnosis["target_dag_exists"]:
            return f"❌ DAG '{ETL_DAG_ID}' tidak ditemukan di Airflow\n\nDAG tersedia: {diagnosis['dags_available']}\nRekomendasi: {', '.join(diagnosis['recommendations'])}"

        # Step 1.5: Check if DAG is paused and auto-unpause if needed
        logger.info("Step 1.5: Checking DAG status...")
        dag_status = _make_airflow_api_request('GET', f'/dags/{ETL_DAG_ID}')
        if dag_status and dag_status.get('is_paused', True):
            logger.info("DAG is paused, attempting to unpause...")
            unpause_result = _make_airflow_api_request(
                'PATCH', f'/dags/{ETL_DAG_ID}', {"is_paused": False})
            if unpause_result and 'dag_id' in unpause_result:
                logger.info(
                    f"Successfully unpaused DAG: {unpause_result['dag_id']}")
            else:
                logger.warning(f"Failed to unpause DAG: {unpause_result}")
                # Step 2: Trigger DAG
                return f"❌ DAG '{ETL_DAG_ID}' ditemukan tapi dalam status paused dan gagal di-unpause.\n\nSilakan unpause DAG secara manual di Airflow UI: {AIRFLOW_BASE_URL}"
        logger.info("Step 2: Triggering ETL DAG...")
        trigger_result = _trigger_dag(ETL_DAG_ID)

        if not trigger_result["success"]:
            # If trigger fails with 404, provide more detailed diagnosis
            error_details = trigger_result.get('details', {})
            if 'status_code' in error_details and error_details['status_code'] == 404:
                # DAG might be broken or not properly parsed
                logger.warning(
                    "DAG not found during trigger - checking DAG health...")

                # Try to get more detailed DAG information
                dag_detail = _make_airflow_api_request(
                    'GET', f'dags/{ETL_DAG_ID}')
                if dag_detail:
                    is_broken = dag_detail.get(
                        'has_task_concurrency_limits', False)
                    last_parsed = dag_detail.get('last_parsed_time')
                    fileloc = dag_detail.get('fileloc', 'unknown')

                    return f"""❌ DAG '{ETL_DAG_ID}' ditemukan tapi tidak dapat di-trigger.

🔍 Detail DAG:
- File lokasi: {fileloc}
- Terakhir di-parse: {last_parsed}
- Status: Mungkin broken atau import error

💡 Kemungkinan solusi:
1. Periksa logs DAG di Airflow UI untuk error parsing
2. Pastikan semua dependencies tersedia di environment ETL
3. Restart Airflow scheduler jika diperlukan

🌐 Periksa di: {AIRFLOW_BASE_URL}/dags/{ETL_DAG_ID}"""

            return f"❌ Gagal menjalankan ETL pipeline: {trigger_result.get('error', 'Unknown error')}"

        dag_run_id = trigger_result["dag_run_id"]

        # Step 3: Wait for completion
        logger.info("Step 3: Waiting for ETL completion...")
        completion_result = _wait_for_dag_completion(
            ETL_DAG_ID, dag_run_id, max_wait_seconds=300)

        if not completion_result["completed"]:
            if "timeout" in completion_result.get("error", "").lower():
                return f"⏳ ETL pipeline masih berjalan (timeout 5 menit tercapai).\n\nDAG Run ID: {dag_run_id}\nAnda dapat memeriksa status di Airflow UI: {AIRFLOW_BASE_URL}"
            else:
                return f"❌ Error menunggu completion ETL: {completion_result.get('error', 'Unknown error')}"

        if completion_result["state"] != "success":
            return f"❌ ETL pipeline gagal dengan status: {completion_result['state']}\n\nDAG Run ID: {dag_run_id}\nPeriksa logs di Airflow UI untuk detail error."

        # Step 4: Get results from XCom
        logger.info("Step 4: Getting ETL results...")
        new_data_count = _get_xcom_value(
            ETL_DAG_ID, dag_run_id, XCOM_TASK_ID, XCOM_KEY)

        # Format response with better messaging for no data scenarios
        duration = completion_result.get("duration", "unknown")

        # Determine data message based on result
        if new_data_count is not None:
            if new_data_count == 0:
                data_message = "📊 Tidak ada data baru yang ditemukan dalam periode ini"
            else:
                data_message = f"📊 Data baru yang berhasil diproses: {new_data_count} record"
        else:
            # XCom value not found - this might indicate the DAG doesn't set this value
            data_message = "📊 ETL berhasil dijalankan, namun informasi jumlah data baru tidak tersedia"

        response_parts = [
            "✅ ETL Pipeline berhasil dijalankan!",
            data_message,
            f"⏱️ Durasi eksekusi: {duration}",
            f"🔗 DAG Run ID: {dag_run_id}"
        ]

        if question and any(keyword in question.lower() for keyword in ["berapa", "jumlah", "count", "how many"]):
            if new_data_count is not None:
                if new_data_count == 0:
                    response_parts.insert(
                        1, f"Untuk menjawab pertanyaan '{question}': Tidak ada data baru yang ditemukan pada periode ini")
                else:
                    response_parts.insert(
                        1, f"Untuk menjawab pertanyaan '{question}': {new_data_count} data baru")
            else:
                response_parts.insert(
                    1, f"Untuk menjawab pertanyaan '{question}': Informasi jumlah data tidak tersedia dari ETL pipeline")

        return "\n".join(response_parts)

    except Exception as e:
        logger.error(f"Unexpected error in ETL tool: {str(e)}")
        return f"❌ Terjadi error tidak terduga: {str(e)}\n\nSilakan periksa logs atau coba lagi."


# Test function untuk debugging
def _test_airflow_connection():
    """Test function untuk debugging koneksi Airflow"""
    print("=== Testing Airflow Connection ===")

    # Test 1: Basic connectivity
    print(f"Testing connection to: {AIRFLOW_BASE_URL}")

    # Test 2: JWT Token
    print("Getting JWT token...")
    token = _get_jwt_token()
    if token:
        print(f"✅ JWT token obtained: {token[:20]}...")
    else:
        print("❌ Failed to get JWT token")
        return

    # Test 3: API call
    print("Testing API call...")
    result = _make_airflow_api_request("GET", "version")
    print(f"API result: {result}")

    # Test 4: Full diagnosis
    print("Running full diagnosis...")
    diagnosis = _diagnose_airflow_connection()
    print(f"Diagnosis: {json.dumps(diagnosis, indent=2)}")


if __name__ == "__main__":
    # Untuk testing
    _test_airflow_connection()
