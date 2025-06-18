<h1 align="center">ICONNET Platform - AI-Powered Telecommunications Management</h1>

<p align="center">
  <a href="https://github.com/rizkyyanuark/intern-iconnet">
    <img src="https://img.shields.io/github/last-commit/rizkyyanuark/intern-iconnet?style=flat-square" alt="Last Commit">
  </a>
  <a href="https://github.com/rizkyyanuark/intern-iconnet">
    <img src="https://img.shields.io/github/languages/top/rizkyyanuark/intern-iconnet?style=flat-square" alt="Top Language">
  </a>
  <a href="https://github.com/rizkyyanuark/intern-iconnet">
    <img src="https://img.shields.io/github/languages/count/rizkyyanuark/intern-iconnet?style=flat-square" alt="Languages Count">
  </a>
  <a href="https://github.com/rizkyyanuark/intern-iconnet">
    <img src="https://img.shields.io/github/repo-size/rizkyyanuark/intern-iconnet?style=flat-square" alt="Repo Size">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="MIT License">
  </a>
</p>

## Feature

- [`Streamlit`](https://streamlit.io/) untuk web interface dan dashboard
- [`LangChain`](https://github.com/langchain-ai/langchain) & [`LangGraph`](https://github.com/langchain-ai/langgraph) untuk agentic workflow AI
- [`PostgreSQL`](https://postgresql.org/) & [`Supabase`](https://supabase.com/) untuk database management
- [`Apache Airflow`](https://airflow.apache.org/) untuk ETL pipeline workflow
- [`Google Gemini AI`](https://ai.google.dev/) untuk LLM integration
- [`Firebase`](https://firebase.google.com/) untuk authentication
- [`pgvector`](https://github.com/pgvector/pgvector) untuk RAG system
- [`uv`](https://docs.astral.sh/uv/) untuk manajemen environment Python

## 🏗️ Architecture

```mermaid
---
config:
  layout: dagre
---
flowchart TD
 subgraph subGraph0["UI Layer"]
        MAIN["Main_Page.py"]
        HOME["Home Page (pages/1 Home Page.py)"]
        ADMIN["Admin Page (pages/2 Admin Page.py)"]
        STATIC["static/css & images"]
  end
 subgraph Controllers["Controllers"]
        HC["features/home/controller.py"]
        AC["features/admin/controller.py"]
  end
 subgraph agent_graph["agent_graph"]
        AG_B["build_graph"]
        AG_BE["agent_backend"]
        AG_AFT["tool_airflow_trigger"]
        AG_RAG["tool_rag"]
        AG_SQL["tool_sql_agent"]
        AG_TAV["tool_tavily_search"]
        AG_VIS["tool_visualization"]
  end
 subgraph Services["Services"]
        ADS["AssetDataService"]
        US["UserService"]
        UDS["UserDataService"]
        ES["EmailService"]
        RAG["RAG"]
        agent_graph
  end
 subgraph subGraph4["Models Layer"]
        M_ALL["models.py"]
        M_USER["user_model.py"]
  end
 subgraph subGraph5["Utils Layer"]
        U_DB["database.py"]
        U_FB["firebase_config.py"]
        U_LC["load_config & load_data_configs"]
        U_CSS["load_css"]
        U_COOK["cookies"]
  end
 subgraph Configs["Configs"]
        CFG_DATA["data_configs.yml"]
        CFG_TOOLS["tools_configs.yml"]
        CFG_TOML["config.toml"]
        CFG_SEC["secret_example.toml"]
  end
 subgraph subGraph7["Streamlit Server"]
        subGraph0
        Controllers
        Services
        subGraph4
        subGraph5
        Configs
  end
 subgraph subGraph9["ETL Pipeline"]
        S2["2️⃣ extract"]
        S3A["3️⃣ transform_asset_data"]
        S3B["3️⃣ transform_user_data"]
        S4["4️⃣ validate_and_splitting"]
        S5["5️⃣ load"]
        S6["6️⃣ send_notification_email"]
  end
 subgraph subGraph10["Data Store"]
        DB["Relational DB"]
        INIT["init.sql"]
        SCHEMA["schema.rb"]
  end
    MAIN -- routes --> HOME & ADMIN
    HOME -- calls --> HC
    ADMIN -- calls --> AC
    HC -- uses --> ADS & UDS & RAG
    AC -- uses --> RAG & ES
    ADS -- reads/writes --> M_ALL
    US -- reads/writes --> M_USER
    UDS -- reads/writes --> M_ALL
    ES -- sends --> SMTP["Email Provider"]
    RAG -- calls --> AIAPI["AI API (OpenAI)"]
    RAG -- stores vectors --> DB
    AG_AFT -- triggers --> AIRFLOW["Airflow Orchestrator"]
    AG_SQL -- queries --> DB
    M_ALL -- SQL --> U_DB
    M_USER -- SQL --> U_DB
    U_DB -- connects --> DB
    CFG_DATA -- loaded by --> U_LC
    CFG_TOOLS -- loaded by --> U_LC
    CFG_TOML -- streamlit --> MAIN
    CFG_SEC -- streamlit --> MAIN
    S2 --> S3B & S3A
    S3A --> S4
    S3B --> S4
    S4 --> S5
    S5 -- batch load --> DB
    S5 --> S6
    INIT -- defines --> DB
    SCHEMA -- defines --> DB
    AIRFLOW --> subGraph9
    FIREBASE_AUTH["Firebase Auth"]
     MAIN:::ui
     HOME:::ui
     ADMIN:::ui
     STATIC:::ui
     HC:::controller
     AC:::controller
     AG_B:::service
     AG_BE:::service
     AG_AFT:::service
     AG_RAG:::service
     AG_SQL:::service
     AG_TAV:::service
     AG_VIS:::service
     ADS:::service
     US:::service
     UDS:::service
     ES:::service
     RAG:::service
     M_ALL:::model
     M_USER:::model
     U_DB:::util
     U_FB:::util
     U_LC:::util
     U_CSS:::util
     U_COOK:::util
     CFG_DATA:::config
     CFG_TOOLS:::config
     CFG_TOML:::config
     CFG_SEC:::config
     DB:::db
     INIT:::files
     SCHEMA:::files
     SMTP:::external
     AIAPI:::external
     AIRFLOW:::external
     FIREBASE_AUTH:::external
    classDef user fill:#B3E5FC,stroke:#0298B0,color:#000
    classDef ui fill:#BBDEFB,stroke:#1976D2,color:#000
    classDef controller fill:#C8E6C9,stroke:#388E3C,color:#000
    classDef service fill:#A5D6A7,stroke:#2E7D32,color:#000
    classDef model fill:#FFE0B2,stroke:#EF6C00,color:#000
    classDef util fill:#DCEDC8,stroke:#558B2F,color:#000
    classDef config fill:#E1BEE7,stroke:#8E24AA,color:#000
    classDef etl fill:#FFCCBC,stroke:#E64A19,color:#000
    classDef data fill:#FFECB3,stroke:#FFA000,color:#000
    classDef db fill:#FFE082,stroke:#FF8F00,color:#000
    classDef files fill:#FFF9C4,stroke:#FBC02D,color:#000
    classDef external fill:#E1F5FE,stroke:#0288D1,color:#000
    click MAIN "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/Main_Page.py"
    click HOME "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/pages/1%20Home%20Page.py"
    click ADMIN "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/pages/2%20Admin%20Page.py"
    click HC "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/features/home/controller.py"
    click AC "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/features/admin/controller.py"
    click AG_B "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/build_graph.py"
    click AG_BE "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/agent_backend.py"
    click AG_AFT "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/tool_airflow_trigger.py"
    click AG_RAG "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/tool_rag.py"
    click AG_SQL "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/tool_sql_agent.py"
    click AG_TAV "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/tool_tavily_search.py"
    click AG_VIS "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/agent_graph/tool_visualization.py"
    click ADS "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/AssetDataService.py"
    click US "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/UserService.py"
    click UDS "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/UserDataService.py"
    click ES "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/EmailService.py"
    click RAG "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/services/RAG.py"
    click M_ALL "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/models/models.py"
    click M_USER "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/models/user_model.py"
    click U_DB "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/utils/database.py"
    click U_FB "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/utils/firebase_config.py"
    click U_LC "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/utils/load_data_configs.py"
    click U_CSS "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/utils/load_css.py"
    click U_COOK "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/utils/cookies.py"
    click CFG_DATA "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/configs/data_configs.yml"
    click CFG_TOOLS "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/core/configs/tools_configs.yml"
    click CFG_TOML "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/.streamlit/config.toml"
    click CFG_SEC "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/.streamlit/secret_example.toml"
    click INIT "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/init.sql"
    click SCHEMA "https://github.com/pt-indonesia-comnets-plus/database-management-web/blob/main/schema.rb"

```

## Instalasi & Setup (Local)

```powershell
# Clone repository
git clone https://github.com/PT-Indonesia-Comnets-Plus/database-management-web.git
cd intern-iconnet

# Setup Python (opsional, untuk development)
uv venv
uv sync

# Copy dan edit file .secret
cp .secret_example.toml
# Edit .secret sesuai kebutuhan

uv run streamlit run Main_Page.py

```

### Fitur Utama

#### 1. Authentication & User Management

- Login/Register melalui Firebase Authentication
- Role-based access (Admin/User)
- Session management

#### 2. AI Assistant (RAG-powered)

Platform memiliki AI assistant yang menggunakan sistem RAG untuk menjawab pertanyaan tentang:

- Data telekomunikasi internal
- Informasi ICONNET dan PLN
- Query database dengan natural language

**Contoh penggunaan:**

```
User: "Apa itu ICONNET dan layanan apa saja yang tersedia?"
AI: "ICONNET adalah anak perusahaan PLN yang menyediakan layanan internet fiber optik..."

User: "Tampilkan data asset di Jakarta"
AI: [Menggunakan SQL Agent untuk query database]
```

#### 3. Database Management dengan AI

- Natural language to SQL conversion
- Visual query builder
- Data visualization otomatis
- ETL pipeline integration

#### 4. Geospatial Data Visualization

- Interactive maps dengan Folium
- Asset location tracking
- Coordinate data cleaning dan standardization

#### 5. ETL Pipeline (Apache Airflow)

Pipeline untuk processing data telekomunikasi:

- Extract dari Google Sheets dan sumber lain
- Transform koordinat dan data asset
- Validate dan split ke multiple tables
- Load ke database PostgreSQL

**Workflow ETL:**

```
1. extract → 2. transform_asset_data → 3. transform_user_data →
4. validate_and_splitting → 5. load → 6. send_notification_email
```

### Chat dengan AI Assistant

**Endpoint internal:** Akses melalui sidebar Streamlit

**Contoh request natural language:**

```
User: "Berapa total asset di Jakarta?"
AI Agent: [Menggunakan SQL Agent untuk query database]

User: "Apa itu ICONNET dan layanan apa saja?"
AI Agent: [Menggunakan RAG untuk cari informasi internal]

User: "Buatkan visualisasi data asset per region"
AI Agent: [Menggunakan Visualization Tool untuk generate chart]
```

**Workflow AI Agent:**

```
User Input → Intent Analysis → Tool Selection →
SQL Agent / RAG Search / Visualization / Web Search →
Response Generation → User Output
```

### ETL Pipeline Trigger

**Endpoint internal:** Akses melalui AI Assistant

**Contoh usage:**

```
User: "Jalankan ETL pipeline untuk data terbaru"
AI Agent: [Menggunakan Airflow Trigger Tool]

User: "Cek status ETL pipeline terakhir"
AI Agent: [Query Airflow API untuk status]
```

## Configuration

### 1. Streamlit Secrets

Edit `.streamlit/secrets.toml`:

```toml
[database]
# PostgreSQL Database Configuration
DB_HOST = ""
DB_NAME = ""
DB_USER = ""
DB_PASSWORD = ""
DB_PORT = ""

[supabase]
# Supabase Configuration (if using Supabase)
url = ""
service_role_key = ""

[firebase]
# Firebase Configuration
firebase_key_json = """
{
  "type": "service_account",
  "project_id": "",
  "private_key_id": "",
  "private_key": "",
  "client_email": "",
  "client_id": "",
  "auth_uri": "",
  "token_uri": "",
  "auth_provider_x509_cert_url": "",
  "client_x509_cert_url": "",
  "universe_domain": ""
}
"""

# This firebase_api is at the root level, consistent with your secrets.toml
firebase_api = ""

# SMTP Configuration
[smtp]
server = ""
port = ""
username = ""
password = ""

# Gemini Configuration
[gemini]
api_key = ""

# Langsmith Configuration
[langsmith]
api_key = ""

# Tavily Configuration
[tavily]
api_key = ""

# Airflow Configuration
[airflow]
base_url = ""
username = ""
password = ""

# Instructions:
# 1. Copy this file to .streamlit/secrets.toml
# 2. Replace all placeholder values with your actual configuration
# 3. Make sure .streamlit/secrets.toml is in your .gitignore
# 4. For local development, you can leave some sections empty to run in demo mode
```

## Deployment ke VPS/Cloud

1. Deploy VM (Ubuntu) di cloud provider (GCP, AWS, Azure)
2. Install PostgreSQL, Docker (opsional)
3. Clone repo & setup environment
4. Konfigurasi `.streamlit/secrets.toml` dengan production values
5. Jalankan:
   ```bash
   pip install uv
   uv venv
   uv sync
   uv run streamlit run Main_Page.py
   ```
6. (Opsional) Setup Nginx reverse proxy & SSL untuk domain

---

> Project ini dikembangkan untuk manajemen infrastruktur telekomunikasi modern dengan AI-powered analytics, siap untuk deployment di cloud maupun on-premise.
