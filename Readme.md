# ICONNET Platform

> Advanced Database Management & AI Assistant Platform for Telecommunications Infrastructure

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11.9-blue?style=flat-square&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.41.1-red?style=flat-square&logo=streamlit)](https://streamlit.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=flat-square&logo=postgresql)](https://postgresql.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.21-green?style=flat-square&logo=chainlink)](https://langchain.com)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-ETL-orange?style=flat-square&logo=apache-airflow)](https://airflow.apache.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/rizkyyanuark/intern-iconnet.git
cd intern-iconnet

# Install dependencies
poetry install && poetry shell

# Configure environment
cp .env.example .env
# Edit .env with your configurations

# Run the application
streamlit run Main_Page.py
```

**Access**: http://localhost:8501

---

## 🌟 Overview

ICONNET Platform is an enterprise-grade database management and AI assistant solution designed for telecommunications infrastructure operations. The platform combines advanced data processing capabilities with intelligent automation through AI-powered agents and external ETL pipeline integration.

### Key Features

🔐 **Authentication & Authorization**

- Firebase-based authentication system
- Role-based access control (Admin/User roles)
- Secure session management

📊 **Database Management**

- PostgreSQL/Supabase integration
- Advanced SQL query interface with AI assistance
- Data visualization and analytics
- Comprehensive ETL pipeline for data transformation

🤖 **AI Assistant with RAG**

- LangChain-powered conversational AI
- Google Gemini AI integration
- Context-aware responses based on internal documents
- Multi-agent system with specialized tools

🗺️ **Geospatial Data Management**

- Interactive maps with Folium
- Asset location tracking and visualization
- Geographic coordinate processing and cleaning

📈 **Interactive Dashboards**

- Real-time data monitoring
- Customizable charts and graphs using Plotly
- Performance metrics visualization

🔄 **ETL Pipeline**

- Automated data processing with Apache Airflow
- Advanced data cleaning and transformation
- Coordinate data standardization
- Multi-table data splitting and normalization

🛠️ **Agent Graph System**

- SQL query generation agent
- RAG-based document search
- Web search integration (Tavily)
- Data visualization tools

## 🏗️ Architecture

The ICONNET platform integrates seamlessly with external ETL systems through the Airflow Trigger Agent Tool, providing a comprehensive data processing workflow that spans both internal and external pipeline systems.

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

### 🔗 Integration Workflow

The architecture demonstrates a sophisticated integration between the ICONNET platform and external ETL systems:

#### 🤖 AI-Triggered ETL Pipeline

1. **User Interaction** → AI Assistant receives ETL processing requests
2. **Agent Graph System** → Routes requests to appropriate tools
3. **Airflow Trigger Tool** → Authenticates and triggers external Airflow jobs via API
4. **External Apache Airflow** → Orchestrates the 7-stage ETL workflow

#### 🔄 7-Stage External ETL Workflow

1. **ensure_database_schema** → Validates and sets up database schema
2. **extract** → Pulls data from Google Sheets and other sources
3. **transform_asset_data** → Processes telecommunications asset data
4. **transform_user_data** → Processes user and connection data
5. **validate_and_splitting** → Validates data integrity and splits into normalized tables
6. **load** → Loads processed data into external Supabase database
7. **send_notification_email** → Sends completion notifications

#### 🔄 Real-time Data Synchronization

- External ETL results are synchronized back to the ICONNET application database
- Email notifications flow back to the application's notification system
- Real-time data replication ensures consistency between systems

#### 🛠️ Dual ETL Capability

- **Internal ETL Pipeline**: Handles direct file uploads and manual data processing
- **External ETL Pipeline**: Manages bulk data processing from external sources
- **Unified Data Flow**: Both systems feed into the same application database structure

## 📁 Project Structure

```mermaid
graph TD
    root["pt-indonesia-comnets-plus-database-management-web/"]

    %% Top-level files
    root --> R1["Readme.md"]
    root --> R2["Dockerfile"]
    root --> R3["ETL_proces.ipynb"]
    root --> R4["etl_proces.py"]
    root --> R5["init.sql"]
    root --> R6["Main_Page.py"]
    root --> R7["pyproject.toml"]
    root --> R8["requirements.txt"]
    root --> R9["schema.rb"]
    root --> R10[".dockerignore"]
    root --> coreDir["core/"]
    root --> dataDir["data/"]
    root --> featuresDir["features/"]
    root --> pagesDir["pages/"]
    root --> staticDir["static/"]
    root --> streamlitDir[".streamlit/"]

    %% core/ module
    subgraph coreDir ["core/"]
        cInit["__init__.py"]
        subgraph configs ["configs/"]
            cfg1["data_configs.yml"]
            cfg2["tools_configs.yml"]
        end
        subgraph models ["models/"]
            mInit["__init__.py"]
            m1["models.py"]
            m2["user_model.py"]
        end
        subgraph services ["services/"]
            sInit["__init__.py"]
            s1["AssetDataService.py"]
            s2["EmailService.py"]
            s3["RAG.py"]
            s4["UserDataService.py"]
            s5["UserService.py"]
            subgraph agent_graph ["agent_graph/"]
                agInit["__init__.py"]
                ag1["agent_backend.py"]
                ag2["build_graph.py"]
                ag3["tool_airflow_trigger.py"]
                ag4["tool_rag.py"]
                ag5["tool_sql_agent.py"]
                ag6["tool_tavily_search.py"]
                ag7["tool_visualization.py"]
            end
        end
        subgraph utils ["utils/"]
            uInit["__init__.py"]
            u1["cookies.py"]
            u2["database.py"]
            u3["firebase_config.py"]
            u4["load_config.py"]
            u5["load_css.py"]
            u6["load_data_configs.py"]
        end
    end

    %% data directory
    subgraph dataDir ["data/"]
        d1["data.xlsx"]
    end

    %% features module
    subgraph featuresDir ["features/"]
        fInit["__init__.py"]
        subgraph admin ["admin/"]
            aInit["__init__.py"]
            a1["controller.py"]
            subgraph adminViews ["views/"]
                av1["dashboard.py"]
                av2["rag.py"]
                av3["rag2.py"]
                av4["verify_users.py"]
            end
        end
        subgraph home ["home/"]
            h1["controller.py"]
            subgraph homeViews ["views/"]
                hv1["chatbot.py"]
                hv2["dashboard.py"]
                hv3["search.py"]
                hv4["update.py"]
                hv5["update_data.py"]
            end
        end
    end

    %% pages directory
    subgraph pagesDir ["pages/"]
        p1["1 Home Page.py"]
        p2["2 Admin Page.py"]
    end

    %% static assets
    subgraph staticDir ["static/"]
        subgraph css ["css/"]
            ccss["style.css"]
        end
        subgraph image ["image/"]
            img1["icon.png"]
            img2["logo_Iconnet.png"]
            img3["logo_iconplus.png"]
        end
    end

    %% streamlit config
    subgraph streamlitDir [".streamlit/"]
        sConf["config.toml"]
        sSec["secret_example.toml"]
    end

    %% Styling
    classDef folder fill:#f2f2f2,stroke:#999,stroke-width:1px
    classDef file fill:#fff,stroke:#ddd,stroke-width:1px
    class coreDir,configs,models,services,utils,dataDir,featuresDir,pagesDir,staticDir,streamlitDir folder
```

## 🛠️ Technology Stack

### Backend

- **Python 3.11.9** - Core programming language
- **Streamlit 1.41.1** - Web application framework
- **PostgreSQL** - Primary database
- **Supabase** - Backend as a Service
- **Firebase** - Authentication service

### AI & Machine Learning

- **LangChain 0.3.21** - AI application framework
- **Google AI (Gemini)** - Large language model
- **LangGraph 0.3.34** - Multi-agent orchestration
- **Tavily** - Search API integration

### Data Processing & Visualization

- **Pandas** - Data manipulation
- **Plotly 5.14.1** - Interactive visualizations
- **Folium 0.14.0** - Geospatial mapping
- **Apache Airflow** - Workflow orchestration

### Development & Deployment

- **Poetry** - Dependency management
- **Docker** - Containerization
- **SQLAlchemy 1.4.54** - Database ORM
- **Pydantic 2.10.6** - Data validation

## 📋 Prerequisites

- Python 3.11.9 or higher
- Poetry (for dependency management)
- PostgreSQL database
- Firebase project (for authentication)
- Google AI API key
- Docker (optional, for containerized deployment)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/rizkyyanuark/intern-iconnet.git
cd intern-iconnet
```

### 2. Install Dependencies

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Activate Virtual Environment

```bash
poetry shell
```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/iconnet_db
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Firebase Configuration
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token

# AI Configuration
GOOGLE_API_KEY=your_google_ai_api_key
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_PROJECT=iconnet-project
TAVILY_API_KEY=your_tavily_api_key

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Airflow Configuration
AIRFLOW_BASE_URL=http://localhost:8080
AIRFLOW_USERNAME=airflow
AIRFLOW_PASSWORD=airflow

# Application Configuration
SECRET_KEY=your_secret_key
DEBUG=True
LOG_LEVEL=INFO
```

### 2. Firebase Setup

1. Create a Firebase project at [Firebase Console](https://console.firebase.google.com/)
2. Enable Authentication and Firestore
3. Download the service account key JSON file
4. Place it in the root directory as `iconnet-intern-firebase-adminsdk.json`

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb iconnet_db

# Run database initialization (if applicable)
python init.sql
```

## 🎯 Usage

### Starting the Application

```bash
# Run the Streamlit application
streamlit run Main_Page.py

# Or use Poetry
poetry run streamlit run Main_Page.py
```

The application will be available at `http://localhost:8501`

### Features Overview

1. **Authentication**: Register/login using the authentication system
2. **Dashboard**: View analytics and key metrics
3. **Data Management**: Upload, view, and manage telecommunications data
4. **AI Assistant**: Interact with the RAG-powered AI for data insights
5. **Map Visualization**: Explore geospatial data on interactive maps
6. **Settings**: Configure user preferences and system settings

## 📚 API Reference

### Core Services API

#### UserService

Handles user authentication, registration, and profile management.

```python
from core.services.UserService import UserService

# Initialize service
user_service = UserService()

# User authentication
user = user_service.authenticate_user(email="user@example.com", password="secure_password")

# User registration
user_service.register_user(
    email="newuser@example.com",
    password="secure_password",
    user_data={
        "full_name": "John Doe",
        "role": "user",
        "department": "IT"
    }
)

# Get user profile
profile = user_service.get_user_profile(user_id)

# Update user permissions
user_service.update_permissions(user_id, permissions_list)
```

#### AssetDataService

Manages telecommunications asset data operations.

```python
from core.services.AssetDataService import AssetDataService

# Initialize service
asset_service = AssetDataService()

# Fetch asset data with filters
assets = asset_service.get_assets(
    filters={
        "region": "Jakarta",
        "device_type": "OLT",
        "status": "active"
    },
    limit=100,
    offset=0
)

# Update asset data
asset_service.update_asset(
    asset_id="AST-001",
    data={
        "status": "maintenance",
        "last_updated": datetime.now(),
        "notes": "Scheduled maintenance"
    }
)

# Bulk asset operations
asset_service.bulk_update(asset_ids, update_data)
```

#### RAGService

Provides intelligent document search and query capabilities.

```python
from core.services.RAG import RAGService

# Initialize service
rag_service = RAGService()

# Query the RAG system
response = rag_service.query(
    question="What are the network performance metrics for Jakarta region?",
    context_limit=5,
    temperature=0.3
)

# Add documents to knowledge base
rag_service.add_documents(
    documents=["doc1.pdf", "doc2.txt"],
    metadata={"category": "network_specs"}
)
```

### AI Agent Tools

#### SQL Agent Tool

Natural language to SQL query conversion and execution.

```python
from core.services.agent_graph.tool_sql_agent import query_asset_database

# Query database with natural language
result = query_asset_database(
    query="Show me all OLT devices in Jakarta with more than 80% utilization",
    return_format="json"
)

# Complex analytical queries
analytics = query_asset_database(
    query="Compare network performance metrics across regions for the last quarter"
)
```

#### Visualization Tool

Create interactive data visualizations from JSON data.

```python
from core.services.agent_graph.tool_visualization import create_visualization

# Create interactive charts
chart = create_visualization(
    data_json=performance_data,
    chart_type="line",
    x_axis="date",
    y_axis="throughput",
    group_by="region",
    title="Network Performance Trends"
)

# Geographic visualizations
map_viz = create_visualization(
    data_json=location_data,
    chart_type="map",
    lat_col="latitude",
    lng_col="longitude",
    color_by="signal_strength"
)
```

#### ETL Pipeline

Advanced data processing pipeline for telecommunications data.

```python
from etl_proces import AssetPipeline

# Initialize pipeline with custom configuration
pipeline = AssetPipeline(
    config={
        "coordinate_cleaning": True,
        "duplicate_removal": True,
        "validation_rules": "strict"
    }
)

# Process data with monitoring
processed_data = pipeline.run(
    dataframe=raw_dataframe,
    source="google_sheets",
    notify_on_completion=True
)

# Access pipeline metrics
metrics = pipeline.get_processing_metrics()
```

## 🔄 ETL Pipeline Architecture

The ICONNET platform features a sophisticated dual-tier ETL architecture designed for scalable telecommunications data processing.

### Pipeline Components

#### 1. **Data Extraction Layer**

- **Excel/CSV Processing**: Native file format support with automatic schema detection
- **Google Sheets Integration**: Real-time data synchronization via Google Sheets API
- **API Connectors**: RESTful API endpoints for external data sources
- **Batch Processing**: Scheduled data extraction with configurable intervals

#### 2. **Data Transformation Engine**

- **Column Mapping**: Intelligent field mapping with fuzzy matching capabilities
- **Coordinate Normalization**: Advanced geospatial data cleaning and standardization
- **Data Type Conversion**: Automatic type inference and conversion
- **Quality Assurance**: Multi-stage validation with configurable rules

#### 3. **Data Loading Framework**

- **Multi-table Splitting**: Automated data normalization across relational tables
- **Incremental Loading**: Delta processing for large datasets
- **Transaction Management**: ACID-compliant data operations
- **Rollback Capabilities**: Automated rollback on failure scenarios

### Advanced Features

#### 🗺️ **Geospatial Data Processing**

The pipeline includes sophisticated coordinate processing capabilities:

```python
# Coordinate formats supported:
# - Decimal degrees: -6.200000, 106.816666
# - Degrees with separators: -6°12'0.0"S, 106°48'60.0"E
# - Mixed formats: -6.2 S, 106.81667 E
# - Malformed coordinates: automatic detection and correction

coordinate_processor = CoordinateProcessor()
cleaned_coords = coordinate_processor.process_coordinates(raw_data)
```

**Processing capabilities:**

- Handles various coordinate formats (decimal, degree-separated, DMS)
- Converts malformed coordinates to standard lat,lng format
- Validates coordinate boundaries for Indonesian geographical regions
- Processes coordinates for OLT, FDT, FAT, and Cluster locations

#### 📊 **Data Normalization**

Automatically splits processed data into normalized database tables:

| Table Name                | Description                       | Key Fields                      |
| ------------------------- | --------------------------------- | ------------------------------- |
| `user_terminals`          | Terminal and equipment data       | device_id, location, status     |
| `clusters`                | Geographic cluster information    | cluster_id, region, coordinates |
| `home_connecteds`         | Home connection statistics        | connection_id, speed, uptime    |
| `dokumentasis`            | Documentation and reference links | doc_id, url, category           |
| `additional_informations` | Additional metadata               | info_id, tags, attributes       |

#### ⚡ **Apache Airflow Integration**

```python
# DAG Configuration
@dag(
    dag_id='iconnet_etl_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
)
def iconnet_etl_dag():
    # Pipeline orchestration
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_from_sources
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_asset_data
    )

    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_to_database
    )

    extract_task >> transform_task >> load_task
```

**Orchestration features:**

- DAG-based workflow management
- Real-time monitoring and alerting
- XCom-based result tracking
- Automated retry mechanisms
- SLA monitoring and notifications

### Performance Optimization

#### **Parallel Processing**

- Multi-threaded data transformation
- Asynchronous I/O operations
- Batch processing optimization
- Memory-efficient streaming

#### **Monitoring & Observability**

- Real-time processing metrics
- Data quality scorecards
- Pipeline performance analytics
- Automated alerting system

### Usage Examples

#### **Basic ETL Operation**

```python
from etl_proces import AssetPipeline
import pandas as pd

# Initialize with custom configuration
pipeline = AssetPipeline(
    config={
        'batch_size': 1000,
        'coordinate_cleaning': True,
        'duplicate_removal': True,
        'validation_level': 'strict',
        'output_format': 'postgresql'
    }
)

# Load and process data
df = pd.read_excel('telecom_assets.xlsx')
result = pipeline.run(df)

# Access processing metrics
print(f"Processed {result.records_processed} records")
print(f"Quality score: {result.quality_score}%")
print(f"Processing time: {result.duration}s")
```

#### **Advanced Pipeline Configuration**

```python
# Custom transformation rules
transformation_config = {
    'column_mappings': {
        'Device Name': 'device_name',
        'Location Coordinates': 'coordinates',
        'Installation Date': 'installed_date'
    },
    'data_types': {
        'device_name': 'string',
        'coordinates': 'geospatial',
        'installed_date': 'datetime'
    },
    'validation_rules': {
        'device_name': {'required': True, 'min_length': 3},
        'coordinates': {'format': 'lat_lng', 'bounds': 'indonesia'}
    }
}

pipeline = AssetPipeline(transformation_config)
```

## 🚀 Development Guide

### Project Setup for Development

#### **Prerequisites**

- Python 3.11+ with Poetry installed
- PostgreSQL 13+ running locally
- Redis server (for Airflow integration)
- Firebase project configured
- Google AI API access

#### **Development Environment Setup**

```bash
# 1. Clone and setup repository
git clone https://github.com/rizkyyanuark/intern-iconnet.git
cd intern-iconnet

# 2. Install development dependencies
poetry install --with dev,test

# 3. Setup pre-commit hooks
poetry run pre-commit install

# 4. Start development services
docker-compose -f docker-compose.dev.yml up -d

# 5. Run database migrations
poetry run alembic upgrade head

# 6. Start development server with hot reload
poetry run streamlit run Main_Page.py --server.runOnSave true
```

### Code Architecture & Standards

#### **Directory Structure Guidelines**

```
core/
├── models/          # Data models and schemas
├── services/        # Business logic and service layer
├── utils/           # Utility functions and helpers
└── configs/         # Configuration files

features/
├── home/           # Feature-specific modules
│   ├── controller.py    # Request handling
│   └── views/          # UI components
└── admin/

pages/              # Streamlit page definitions
static/             # Static assets (CSS, images)
tests/              # Test suites
```

#### **Coding Standards**

```python
# Type hints are mandatory
def process_asset_data(
    data: pd.DataFrame,
    config: Dict[str, Any]
) -> ProcessingResult:
    """
    Process telecommunications asset data.

    Args:
        data: Raw asset data from source systems
        config: Processing configuration parameters

    Returns:
        ProcessingResult containing processed data and metrics

    Raises:
        ValidationError: When data validation fails
        ProcessingError: When transformation fails
    """
    pass

# Use Pydantic models for data validation
class AssetModel(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=50)
    coordinates: Optional[Tuple[float, float]] = None
    installation_date: datetime
    status: Literal["active", "inactive", "maintenance"]

    class Config:
        validate_assignment = True
```

#### **Testing Guidelines**

```python
# Unit tests with pytest
def test_coordinate_processing():
    processor = CoordinateProcessor()
    result = processor.clean_coordinates("-6.2, 106.81667")
    assert result == (-6.2, 106.81667)

# Integration tests
def test_etl_pipeline_end_to_end():
    pipeline = AssetPipeline(test_config)
    result = pipeline.run(sample_data)
    assert result.success is True
    assert result.records_processed > 0

# Performance tests
@pytest.mark.performance
def test_large_dataset_processing():
    large_dataset = generate_test_data(records=100000)
    start_time = time.time()
    pipeline.run(large_dataset)
    duration = time.time() - start_time
    assert duration < 300  # Should complete within 5 minutes
```

### Development Workflow

#### **Feature Development Process**

1. **Feature Branch Creation**

   ```bash
   git checkout -b feature/new-etl-connector
   ```

2. **Development with Testing**

   ```bash
   # Run tests continuously during development
   poetry run pytest --watch

   # Code quality checks
   poetry run black .
   poetry run isort .
   poetry run mypy core/
   ```

3. **Performance Profiling**

   ```bash
   # Profile ETL pipeline performance
   poetry run python -m cProfile -o profile.stats etl_proces.py

   # Memory usage analysis
   poetry run memory_profiler main_process.py
   ```

4. **Documentation Updates**

   ```bash
   # Generate API documentation
   poetry run sphinx-build -b html docs/ docs/_build/

   # Update README if needed
   # Ensure all new features are documented
   ```

#### **Code Review Checklist**

- [ ] Type hints added for all function signatures
- [ ] Unit tests cover new functionality (minimum 80% coverage)
- [ ] Integration tests validate end-to-end workflows
- [ ] Performance impact assessed for large datasets
- [ ] Security considerations addressed
- [ ] Documentation updated
- [ ] Error handling and logging implemented
- [ ] Database migrations included if schema changes

### Debugging & Troubleshooting

#### **Common Development Issues**

| Issue                             | Solution                                 |
| --------------------------------- | ---------------------------------------- |
| Poetry installation fails         | Update pip: `pip install --upgrade pip`  |
| Streamlit hot reload not working  | Use `--server.runOnSave true` flag       |
| Database connection errors        | Check PostgreSQL service and credentials |
| AI API rate limits                | Implement exponential backoff            |
| Memory issues with large datasets | Use chunk processing                     |

#### **Logging Configuration**

```python
import logging
from core.utils.logging_config import setup_logging

# Development logging
setup_logging(level=logging.DEBUG, format='detailed')

# Production logging
setup_logging(level=logging.INFO, format='json')
```

#### **Performance Monitoring**

```python
# Add performance monitoring to critical paths
from core.utils.monitoring import monitor_performance

@monitor_performance
def process_large_dataset(data: pd.DataFrame) -> ProcessingResult:
    # Function automatically tracked for performance metrics
    pass
```

## 🔄 ETL Pipeline Integration

The ICONNET platform integrates with external ETL pipeline for comprehensive data processing:

```mermaid
flowchart TD
    %% External ETL Pipeline
    subgraph "🌐 External ETL Pipeline"
        AF["⚡ Apache Airflow 3.0.0"]:::orchestration
        GS["📊 Google Sheets Sources"]:::dataSource
        REDIS["🔄 Redis Message Broker"]:::orchestration

        subgraph "🔄 ETL Process"
            EXTRACT_EXT["📥 Extract"]:::processing
            TRANSFORM_EXT["🔄 Transform"]:::processing
            VALIDATE_EXT["✅ Validate"]:::processing
            LOAD_EXT["📤 Load"]:::processing
        end

        SUPA_EXT["🚀 Supabase Database"]:::storage
        EMAIL_EXT["📧 Monitoring"]:::monitoring
    end

    %% ICONNET Platform
    subgraph "🖥️ ICONNET Platform"
        UI["📱 Streamlit Interface"]:::frontend
        SERVICES["⚙️ Core Services"]:::service

        subgraph "🤖 AI Agent System"
            AIRFLOW_TOOL["🌪️ Airflow Trigger Tool"]:::tool
            OTHER_AGENTS["🛠️ Other Agent Tools"]:::tool
        end

        ETL_INTERNAL["📥 Internal ETL Pipeline"]:::etl
        DB_INTERNAL["🗄️ Application Database"]:::database
    end

    %% Integration Flow
    GS --> EXTRACT_EXT
    EXTRACT_EXT --> TRANSFORM_EXT
    TRANSFORM_EXT --> VALIDATE_EXT
    VALIDATE_EXT --> LOAD_EXT
    LOAD_EXT --> SUPA_EXT

    %% Key Integration Points
    AIRFLOW_TOOL -.->|"Trigger Jobs"| AF
    SUPA_EXT -.->|"Real-time Sync"| DB_INTERNAL
    EMAIL_EXT -.->|"Notifications"| SERVICES

    UI --> SERVICES
    SERVICES --> AIRFLOW_TOOL
    ETL_INTERNAL --> DB_INTERNAL

    %% Styling
    classDef dataSource fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef orchestration fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef processing fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef monitoring fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef service fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef tool fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef etl fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef database fill:#e0f2f1,stroke:#00695c,stroke-width:2px
```

## 🚀 Deployment

### Production Deployment Options

#### **1. Docker Containerized Deployment**

**Prerequisites:**

- Docker Engine 20.10+
- Docker Compose v2+
- 4GB+ RAM available
- SSL certificate for HTTPS

**Quick Production Setup:**

```bash
# 1. Clone and configure
git clone https://github.com/rizkyyanuark/intern-iconnet.git
cd intern-iconnet

# 2. Production environment setup
cp .env.example .env.production
# Edit .env.production with production values

# 3. Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify deployment
curl -f http://localhost:8501/health || echo "Deployment verification failed"
```

**Production Docker Compose:**

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  iconnet-app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8501:8501"
    environment:
      - ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - iconnet-app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### **2. Cloud Platform Deployment**

##### **AWS Deployment**

```bash
# Using AWS ECS with Fargate
aws ecs create-cluster --cluster-name iconnet-cluster

# Deploy using CloudFormation
aws cloudformation deploy \
  --template-file aws-infrastructure.yml \
  --stack-name iconnet-stack \
  --parameter-overrides \
    DatabasePassword=${DB_PASSWORD} \
    DomainName=${DOMAIN_NAME}
```

##### **Google Cloud Platform**

```bash
# Deploy to Google Cloud Run
gcloud run deploy iconnet-platform \
  --image gcr.io/${PROJECT_ID}/iconnet:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --env-vars-file .env.production
```

##### **Microsoft Azure**

```bash
# Deploy to Azure Container Instances
az container create \
  --resource-group iconnet-rg \
  --name iconnet-app \
  --image iconnet/platform:latest \
  --memory 2 \
  --cpu 2 \
  --environment-variables @env-vars.txt \
  --ports 8501
```

### Infrastructure Requirements

#### **Minimum Production Requirements**

| Component    | Specification  | Notes                                |
| ------------ | -------------- | ------------------------------------ |
| **CPU**      | 2 vCPUs        | 4+ vCPUs recommended for high-load   |
| **Memory**   | 4GB RAM        | 8GB+ recommended with large datasets |
| **Storage**  | 20GB SSD       | Additional storage for data and logs |
| **Database** | PostgreSQL 13+ | Managed service recommended          |
| **Network**  | 1Gbps          | For large ETL operations             |

#### **Recommended Production Architecture**

```mermaid
graph TB
    subgraph "🌐 External Access"
        USERS["👥 Users"]
        LB["⚖️ Load Balancer"]
    end

    subgraph "🔒 Security Layer"
        WAF["🛡️ Web Application Firewall"]
        SSL["🔐 SSL Termination"]
    end

    subgraph "🖥️ Application Tier"
        APP1["📱 ICONNET Instance 1"]
        APP2["📱 ICONNET Instance 2"]
        APP3["📱 ICONNET Instance 3"]
    end

    subgraph "💾 Data Tier"
        DB_PRIMARY["🗄️ PostgreSQL Primary"]
        DB_REPLICA["🗄️ PostgreSQL Replica"]
        REDIS["⚡ Redis Cache"]
        S3["📦 Object Storage"]
    end

    subgraph "🔄 Processing Tier"
        AIRFLOW["🌪️ Airflow Cluster"]
        WORKER1["⚙️ ETL Worker 1"]
        WORKER2["⚙️ ETL Worker 2"]
    end

    subgraph "📊 Monitoring"
        PROMETHEUS["📈 Prometheus"]
        GRAFANA["📊 Grafana"]
        LOGS["📝 Centralized Logging"]
    end

    USERS --> LB
    LB --> WAF
    WAF --> SSL
    SSL --> APP1 & APP2 & APP3

    APP1 & APP2 & APP3 --> DB_PRIMARY
    DB_PRIMARY --> DB_REPLICA
    APP1 & APP2 & APP3 --> REDIS
    APP1 & APP2 & APP3 --> S3

    APP1 & APP2 & APP3 --> AIRFLOW
    AIRFLOW --> WORKER1 & WORKER2

    APP1 & APP2 & APP3 --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    APP1 & APP2 & APP3 --> LOGS
```

### Security Configuration

#### **SSL/TLS Setup**

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name iconnet.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://iconnet-app:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### **Environment Security**

```bash
# Production environment variables
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
export SECRET_KEY="your-256-bit-secret-key"
export ENVIRONMENT="production"
export DEBUG="false"
export LOG_LEVEL="INFO"

# Security headers
export SECURE_SSL_REDIRECT="true"
export SECURE_HSTS_SECONDS="31536000"
export SECURE_CONTENT_TYPE_NOSNIFF="true"
export SECURE_BROWSER_XSS_FILTER="true"
```

### Monitoring & Observability

#### **Health Checks**

```python
# health_check.py
from fastapi import APIRouter
from core.utils.database import check_database_connection
from core.utils.redis import check_redis_connection

router = APIRouter()

@router.get("/health")
async def health_check():
    checks = {
        "database": await check_database_connection(),
        "redis": await check_redis_connection(),
        "ai_service": await check_ai_service(),
        "storage": await check_storage_connection()
    }

    status = "healthy" if all(checks.values()) else "unhealthy"
    return {"status": status, "checks": checks}
```

#### **Prometheus Metrics**

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Application metrics
request_count = Counter('iconnet_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('iconnet_request_duration_seconds', 'Request duration')
active_users = Gauge('iconnet_active_users', 'Number of active users')
etl_processing_time = Histogram('iconnet_etl_duration_seconds', 'ETL processing time')
```

#### **Alerting Rules**

```yaml
# alerting_rules.yml
groups:
  - name: iconnet_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(iconnet_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseConnectionDown
        expr: iconnet_database_up == 0
        for: 1m
        annotations:
          summary: "Database connection is down"

      - alert: ETLProcessingDelay
        expr: iconnet_etl_duration_seconds > 3600
        for: 10m
        annotations:
          summary: "ETL processing taking too long"
```

### Backup & Recovery

#### **Database Backup Strategy**

```bash
#!/bin/bash
# backup_database.sh

# Daily full backup
pg_dump $DATABASE_URL | gzip > "/backups/iconnet_$(date +%Y%m%d).sql.gz"

# Weekly backup retention
find /backups -name "iconnet_*.sql.gz" -mtime +7 -delete

# Upload to cloud storage
aws s3 cp "/backups/iconnet_$(date +%Y%m%d).sql.gz" s3://iconnet-backups/
```

#### **Disaster Recovery Plan**

1. **RTO (Recovery Time Objective)**: 4 hours
2. **RPO (Recovery Point Objective)**: 1 hour
3. **Backup Strategy**:
   - Continuous WAL archiving
   - Daily full backups
   - Real-time database replication
4. **Recovery Procedures**:
   - Automated failover to standby database
   - Application restart with health checks
   - Data verification and integrity checks

### Performance Optimization

#### **Application Tuning**

```python
# production_config.py
PRODUCTION_CONFIG = {
    'database': {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'pool_recycle': 3600
    },
    'cache': {
        'redis_max_connections': 50,
        'cache_ttl': 3600,
        'cache_key_prefix': 'iconnet:'
    },
    'etl': {
        'batch_size': 10000,
        'parallel_workers': 4,
        'memory_limit': '2GB'
    }
}
```

#### **Database Optimization**

```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_assets_region_status ON assets(region, status);
CREATE INDEX CONCURRENTLY idx_users_email_hash ON users USING hash(email);
CREATE INDEX CONCURRENTLY idx_etl_logs_timestamp ON etl_logs(created_at DESC);

-- Query optimization
ANALYZE;
VACUUM ANALYZE;
```

## 🤝 Contributing

We welcome contributions to the ICONNET Platform! This section provides comprehensive guidelines for contributors.

### Contributing Guidelines

#### **Code of Conduct**

All contributors must adhere to our Code of Conduct:

- Be respectful and inclusive
- Use welcoming and professional language
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

#### **Getting Started**

1. **Fork the Repository**

   ```bash
   # Fork on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/intern-iconnet.git
   cd intern-iconnet
   ```

2. **Set Up Development Environment**

   ```bash
   # Install dependencies
   poetry install --with dev,test

   # Setup pre-commit hooks
   pre-commit install

   # Create feature branch
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**

   ```bash
   # Write your code
   # Add tests
   # Update documentation

   # Run tests
   poetry run pytest

   # Check code quality
   poetry run black .
   poetry run isort .
   poetry run mypy .
   ```

#### **Contribution Types**

| Type                 | Description                | Requirements                 |
| -------------------- | -------------------------- | ---------------------------- |
| 🐛 **Bug Fix**       | Fix existing functionality | Issue reference, tests       |
| ✨ **Feature**       | Add new functionality      | Design document, tests, docs |
| 📚 **Documentation** | Improve docs/README        | Clear writing, examples      |
| 🔧 **Refactoring**   | Code improvements          | No behavior changes, tests   |
| ⚡ **Performance**   | Optimize existing code     | Benchmarks, measurements     |

#### **Pull Request Process**

1. **Pre-submission Checklist**

   - [ ] All tests pass (`poetry run pytest`)
   - [ ] Code coverage ≥ 80% for new code
   - [ ] Code formatted (`black`, `isort`)
   - [ ] Type checking passes (`mypy`)
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated

2. **PR Description Template**

   ```markdown
   ## Description

   Brief description of changes made

   ## Type of Change

   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement

   ## Testing

   - [ ] Unit tests added/updated
   - [ ] Integration tests pass
   - [ ] Manual testing completed

   ## Checklist

   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] No breaking changes (or clearly documented)
   ```

3. **Review Process**
   - Automated checks must pass
   - At least one maintainer approval required
   - Address all review feedback
   - Squash commits before merge

#### **Development Workflow**

```bash
# 1. Start with latest main
git checkout main
git pull upstream main

# 2. Create feature branch
git checkout -b feature/etl-performance-optimization

# 3. Develop with TDD approach
# Write test -> Write code -> Refactor -> Repeat

# 4. Commit with conventional format
git commit -m "feat(etl): improve processing speed by 40%

- Implement parallel processing for coordinate cleaning
- Add batch processing for large datasets
- Update tests and documentation

Resolves: #123"

# 5. Push and create PR
git push origin feature/etl-performance-optimization
```

#### **Commit Message Convention**

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples:**

```bash
feat(auth): add multi-factor authentication support
fix(etl): resolve coordinate parsing for malformed data
docs(api): update RAG service documentation
perf(database): optimize asset queries with proper indexing
```

### Issue Reporting

#### **Bug Reports**

Use the bug report template:

```markdown
**Bug Description**
A clear description of the bug

**Steps to Reproduce**

1. Navigate to...
2. Click on...
3. See error

**Expected Behavior**
What should have happened

**Environment**

- OS: [e.g., Windows 11, Ubuntu 20.04]
- Python Version: [e.g., 3.11.9]
- Browser: [e.g., Chrome 96]

**Additional Context**
Screenshots, logs, or other relevant information
```

#### **Feature Requests**

Use the feature request template:

```markdown
**Feature Summary**
Brief description of the proposed feature

**Problem Statement**
What problem does this solve?

**Proposed Solution**
Detailed description of the proposed implementation

**Alternatives Considered**
Other solutions you've considered

**Additional Context**
Mockups, examples, or related issues
```

### Community

#### **Communication Channels**

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussions
- **Discord**: Real-time chat and support (link in repository)
- **Email**: security@iconnet.com for security issues

#### **Recognition**

Contributors are recognized in:

- GitHub contributors page
- CONTRIBUTORS.md file
- Release notes for significant contributions
- Annual contributor appreciation posts

#### **Maintainer Responsibilities**

Current maintainers:

- Add your maintainer info here

Maintainer duties:

- Review pull requests within 48 hours
- Triage issues within 24 hours
- Maintain CI/CD pipeline
- Ensure code quality standards
- Guide architectural decisions

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### License Summary

- ✅ **Commercial use** - Use in commercial projects
- ✅ **Modification** - Modify the source code
- ✅ **Distribution** - Distribute the software
- ✅ **Private use** - Use for private projects
- ❌ **Liability** - No warranty provided
- ❌ **Patent rights** - No patent rights granted

### Third-Party Licenses

This project uses open-source libraries with their respective licenses:

| Library        | License            | Usage                  |
| -------------- | ------------------ | ---------------------- |
| Streamlit      | Apache 2.0         | Web framework          |
| LangChain      | MIT                | AI framework           |
| PostgreSQL     | PostgreSQL License | Database               |
| Redis          | BSD 3-Clause       | Caching                |
| Apache Airflow | Apache 2.0         | Workflow orchestration |

---

## 🙏 Acknowledgments

### Core Team

- **ICONNET Development Team** - Feature development and testing
- **Community Contributors** - Bug reports, feature requests, and improvements

### Special Thanks

- **Streamlit Team** - For the excellent web framework
- **LangChain Community** - For AI development tools
- **PostgreSQL Community** - For robust database solutions
- **Open Source Contributors** - For the libraries and tools that make this project possible

### Inspiration

This project was inspired by the need for enterprise-grade telecommunications infrastructure management tools that combine traditional database operations with modern AI capabilities.

---

## 📞 Support & Contact

### Getting Help

1. **Documentation**: Start with this README and inline code documentation
2. **GitHub Issues**: Search existing issues or create a new one
3. **GitHub Discussions**: Community Q&A and general discussions
4. **Discord Community**: Real-time support and discussion

### Support Levels

| Type                  | Response Time | Channels             |
| --------------------- | ------------- | -------------------- |
| **Bug Reports**       | 24-48 hours   | GitHub Issues        |
| **Feature Requests**  | 1-2 weeks     | GitHub Issues        |
| **General Questions** | 2-5 days      | GitHub Discussions   |
| **Security Issues**   | 24 hours      | security@iconnet.com |

### Contact Information

- **Project Repository**: [github.com/rizkyyanuark/intern-iconnet](https://github.com/rizkyyanuark/intern-iconnet)
- **Documentation**: Available in `/docs` directory
- **Security Contact**: security@iconnet.com
- **Business Inquiries**: business@iconnet.com

---

<div align="center">

**Built with ❤️ by the ICONNET Team**

[![GitHub Stars](https://img.shields.io/github/stars/rizkyyanuark/intern-iconnet?style=social)](https://github.com/rizkyyanuark/intern-iconnet/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/rizkyyanuark/intern-iconnet?style=social)](https://github.com/rizkyyanuark/intern-iconnet/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/rizkyyanuark/intern-iconnet)](https://github.com/rizkyyanuark/intern-iconnet/issues)

</div>
