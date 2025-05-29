# ICONNET Database Management & AI Assistant Platform

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11.9-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.41.1-red?style=flat-square&logo=streamlit)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?style=flat-square&logo=postgresql)
![LangChain](https://img.shields.io/badge/LangChain-0.3.21-green?style=flat-square&logo=chainlink)
![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-ETL-orange?style=flat-square&logo=apache-airflow)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

_A comprehensive database management and AI assistant platform for telecommunications infrastructure with advanced ETL pipeline and RAG capabilities_

</div>

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

## 🌟 Overview

ICONNET Database Management & AI Assistant Platform is a sophisticated web application built with Streamlit that provides comprehensive database management capabilities for telecommunications infrastructure. The platform integrates advanced AI features, including a RAG (Retrieval-Augmented Generation) system, to assist users in data analysis, querying, and decision-making processes.

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

## 📚 API Documentation

### Core Services

#### UserService

```python
from core.services.UserService import UserService

# Initialize service
user_service = UserService()

# User authentication
user = user_service.authenticate_user(email, password)

# User registration
user_service.register_user(email, password, user_data)
```

#### AssetDataService

```python
from core.services.AssetDataService import AssetDataService

# Initialize service
asset_service = AssetDataService()

# Fetch asset data
assets = asset_service.get_assets(filters)

# Update asset data
asset_service.update_asset(asset_id, data)
```

#### RAGService

```python
from core.services.RAG import RAGService

# Initialize service
rag_service = RAGService()

# Query the RAG system
response = rag_service.query("What are the network performance metrics?")
```

### Agent Graph Tools

#### SQL Agent Tool

```python
from core.services.agent_graph.tool_sql_agent import query_asset_database

# Query database with natural language
result = query_asset_database("Show me all OLT devices in Jakarta")
```

#### Visualization Tool

```python
from core.services.agent_graph.tool_visualization import create_visualization

# Create interactive charts
chart = create_visualization(data_json, "bar", "region", "count")
```

#### ETL Pipeline

```python
from etl_proces import AssetPipeline

# Initialize pipeline
pipeline = AssetPipeline()

# Process data
processed_data = pipeline.run(raw_dataframe)
```

## 🔄 ETL Pipeline Details

The ICONNET platform includes a sophisticated ETL (Extract, Transform, Load) pipeline implemented in the `AssetPipeline` class that handles telecommunications asset data processing.

### Pipeline Components

1. **Data Extraction**

   - Excel/CSV file processing
   - Google Sheets integration
   - API data connectors

2. **Data Transformation**

   - Column name standardization and mapping
   - Coordinate data cleaning and processing
   - Data type conversion and validation
   - Duplicate removal and deduplication

3. **Data Loading**
   - Multi-table data splitting
   - PostgreSQL database insertion
   - Data integrity validation

### Key Features

#### Coordinate Processing

The pipeline includes advanced coordinate cleaning capabilities:

- Handles various coordinate formats (decimal, degree-separated, etc.)
- Converts malformed coordinates to standard lat,lng format
- Processes coordinates for OLT, FDT, FAT, and Cluster locations

#### Data Splitting

Automatically splits processed data into normalized database tables:

- `user_terminals` - Terminal and equipment data
- `clusters` - Geographic cluster information
- `home_connecteds` - Home connection statistics
- `dokumentasis` - Documentation and reference links
- `additional_informations` - Additional metadata

#### Integration with Airflow

- Automated pipeline execution via Apache Airflow
- DAG-based workflow orchestration
- Real-time monitoring and alerting
- XCom-based result tracking

### Usage Example

```python
from etl_proces import AssetPipeline
import pandas as pd

# Initialize the pipeline
pipeline = AssetPipeline()

# Load your data
df = pd.read_excel('asset_data.xlsx')

# Run the complete ETL process
processed_data = pipeline.run(df)

# Get split data for different tables
split_data = pipeline.split_data(processed_data)
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

### Integration Benefits

- **Unified Data Flow**: External ETL handles bulk processing, ICONNET manages real-time operations
- **AI-Controlled Pipeline**: Agent system can trigger and monitor external ETL jobs
- **Real-time Sync**: Automatic data synchronization between systems
- **Centralized Monitoring**: Integrated alerts and notifications

