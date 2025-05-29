# ICONNET Database Management & AI Assistant Platform

<div align="center">

![ICONNET Logo](https://img.shields.io/badge/ICONNET-Database%20Management-blue?style=for-the-badge)
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
flowchart TD
    %% External Services & Data Sources
    subgraph "🌐 External Services & Data Sources"
        direction TB
        FIREBASE_AUTH["🔥 Firebase Authentication"]:::external
        GEMINI_AI["🤖 Google AI Gemini"]:::external
        TAVILY_API["🔍 Tavily Search API"]:::external
        LANGSMITH["📊 LangSmith Monitoring"]:::external
        GOOGLE_CREDS["🔑 Google Credentials"]:::external
        GOOGLE_SHEETS["📊 Google Sheets Data Sources"]:::external
    end

    %% ICONNET Platform Core
    subgraph "🖥️ ICONNET Platform"
        direction TB

        %% Frontend Layer
        subgraph "📱 Frontend Layer"
            direction TB
            MAIN_PAGE["🏠 Main Page<br/>Authentication & Navigation"]:::frontend

            subgraph "👤 User Interface"
                HOME_DASH["🏠 Home Dashboard"]:::frontend
                AI_CHAT["💬 AI Assistant"]:::frontend
                DATA_SEARCH["🔍 Data Search"]:::frontend
                DATA_UPDATE["📝 Data Update"]:::frontend
            end

            subgraph "👨‍💼 Admin Interface"
                ADMIN_DASH["👨‍💼 Admin Dashboard"]:::frontend
                USER_VERIFY["✅ User Verification"]:::frontend
                RAG_MGMT["🤖 RAG Management"]:::frontend
            end

            MAIN_PAGE --> HOME_DASH
            MAIN_PAGE --> ADMIN_DASH
            HOME_DASH --> AI_CHAT
            HOME_DASH --> DATA_SEARCH
            HOME_DASH --> DATA_UPDATE
            ADMIN_DASH --> USER_VERIFY
            ADMIN_DASH --> RAG_MGMT
        end

        %% Core Services
        subgraph "⚙️ Core Services Layer"
            direction TB

            subgraph "👤 User Management"
                USER_SERVICE["UserService<br/>Authentication & Authorization"]:::service
                USER_DATA_SERVICE["UserDataService<br/>User Data Management"]:::service
                EMAIL_SERVICE["EmailService<br/>Notification System"]:::service
            end

            subgraph "📊 Data & AI Services"
                ASSET_SERVICE["AssetDataService<br/>Telecommunications Data"]:::service
                RAG_SERVICE["RAGService<br/>Document Retrieval & AI"]:::service
            end
        end

        %% AI & Agent Graph System
        subgraph "🤖 AI & Agent Graph System"
            direction TB
            GRAPH_BUILD["🏗️ Build Graph<br/>Agent Orchestration"]:::ai
            AGENT_BACKEND["🔧 Agent Backend<br/>Multi-Agent Coordination"]:::ai

            subgraph "🛠️ Specialized Agent Tools"
                direction TB
                SQL_AGENT["🗃️ SQL Agent Tool<br/>Database Queries"]:::tool
                RAG_AGENT["📚 RAG Tool<br/>Document Search"]:::tool
                VIZ_AGENT["📈 Visualization Tool<br/>Chart Generation"]:::tool
                SEARCH_AGENT["🔍 Tavily Search Tool<br/>Web Search"]:::tool
                AIRFLOW_TRIGGER["🌪️ Airflow Trigger Tool<br/>🔗 External ETL Control"]:::tool_critical
            end

            GRAPH_BUILD --> AGENT_BACKEND
            AGENT_BACKEND --> SQL_AGENT
            AGENT_BACKEND --> RAG_AGENT
            AGENT_BACKEND --> VIZ_AGENT
            AGENT_BACKEND --> SEARCH_AGENT
            AGENT_BACKEND --> AIRFLOW_TRIGGER
        end

        %% Internal ETL Pipeline
        subgraph "🔄 Internal ETL Pipeline System"
            direction TB
            INTERNAL_ETL["📥 AssetPipeline<br/>Internal ETL Controller"]:::etl

            subgraph "⚙️ Internal ETL Processing"
                direction LR
                INT_EXTRACT["1️⃣ Data Extraction<br/>Excel/CSV Processing"]:::etl_process
                INT_CLEAN["2️⃣ Data Cleaning<br/>Column Standardization"]:::etl_process
                INT_COORD["3️⃣ Coordinate Processing<br/>Geospatial Data Cleaning"]:::etl_process
                INT_TRANSFORM["4️⃣ Data Transformation<br/>Type Conversion & Validation"]:::etl_process
                INT_SPLIT["5️⃣ Data Splitting<br/>Multi-Table Normalization"]:::etl_process
                INT_LOAD["6️⃣ Data Loading<br/>Database Insertion"]:::etl_process

                INT_EXTRACT --> INT_CLEAN
                INT_CLEAN --> INT_COORD
                INT_COORD --> INT_TRANSFORM
                INT_TRANSFORM --> INT_SPLIT
                INT_SPLIT --> INT_LOAD
            end

            INTERNAL_ETL --> INT_EXTRACT
        end

        %% Application Database
        subgraph "💾 Application Data Storage"
            direction TB
            APP_DB["🗄️ Application Database<br/>PostgreSQL/Supabase"]:::database

            subgraph "📋 Database Tables"
                direction TB
                USER_TERMINALS["user_terminals<br/>Terminal Equipment Data"]:::db_table
                CLUSTERS["clusters<br/>Geographic Cluster Data"]:::db_table
                HOME_CONNECTED["home_connecteds<br/>Connection Statistics"]:::db_table
                DOKUMENTASI["dokumentasis<br/>Documentation Links"]:::db_table
                ADDITIONAL_INFO["additional_informations<br/>Metadata Storage"]:::db_table
            end

            APP_DB --> USER_TERMINALS
            APP_DB --> CLUSTERS
            APP_DB --> HOME_CONNECTED
            APP_DB --> DOKUMENTASI
            APP_DB --> ADDITIONAL_INFO
        end
    end

    %% External ETL Pipeline System
    subgraph "🌟 External ETL Pipeline System"
        direction TB
        EXT_AIRFLOW["⚡ Apache Airflow 3.0.0<br/>External Orchestration"]:::external_etl
        EXT_REDIS["🔄 Redis Message Broker"]:::external_etl

        subgraph "🔄 7-Stage External ETL Workflow"
            direction LR
            STAGE1["1️⃣ ensure_database_schema<br/>Database Schema Setup"]:::external_process
            STAGE2["2️⃣ extract<br/>Data Source Extraction"]:::external_process
            STAGE3["3️⃣ transform_asset_data<br/>Asset Data Processing"]:::external_process
            STAGE4["4️⃣ transform_user_data<br/>User Data Processing"]:::external_process
            STAGE5["5️⃣ validate_and_splitting<br/>Data Validation & Splitting"]:::external_process
            STAGE6["6️⃣ load<br/>Data Loading to Database"]:::external_process
            STAGE7["7️⃣ send_notification_email<br/>Email Notifications"]:::external_process

            STAGE1 --> STAGE2
            STAGE2 --> STAGE3
            STAGE3 --> STAGE4
            STAGE4 --> STAGE5
            STAGE5 --> STAGE6
            STAGE6 --> STAGE7
        end

        EXT_SUPABASE["🚀 External Supabase Database<br/>ETL Target Database"]:::external_db

        EXT_AIRFLOW --> STAGE1
        EXT_REDIS -.->|"Message Queue"| EXT_AIRFLOW
    end

    %% Key Integration Connections
    %% User Interface Connections
    MAIN_PAGE --> USER_SERVICE
    HOME_DASH --> ASSET_SERVICE
    AI_CHAT --> RAG_SERVICE
    DATA_SEARCH --> ASSET_SERVICE
    DATA_UPDATE --> ASSET_SERVICE
    ADMIN_DASH --> USER_SERVICE
    USER_VERIFY --> USER_DATA_SERVICE
    RAG_MGMT --> RAG_SERVICE

    %% Service to External API Connections
    USER_SERVICE --> FIREBASE_AUTH
    USER_DATA_SERVICE --> APP_DB
    EMAIL_SERVICE --> FIREBASE_AUTH
    ASSET_SERVICE --> APP_DB
    RAG_SERVICE --> GEMINI_AI

    %% AI Agent System Connections
    RAG_SERVICE --> GRAPH_BUILD
    ASSET_SERVICE --> AGENT_BACKEND
    SQL_AGENT --> APP_DB
    RAG_AGENT --> GEMINI_AI
    VIZ_AGENT --> GEMINI_AI
    SEARCH_AGENT --> TAVILY_API

    %% Critical Integration: Airflow Trigger Tool to External ETL
    AIRFLOW_TRIGGER -.->|"🔗 API Trigger<br/>JWT Authentication"| EXT_AIRFLOW

    %% Internal ETL Connections
    ASSET_SERVICE --> INTERNAL_ETL
    INT_LOAD --> APP_DB
    INT_LOAD --> USER_TERMINALS
    INT_LOAD --> CLUSTERS
    INT_LOAD --> HOME_CONNECTED
    INT_LOAD --> DOKUMENTASI
    INT_LOAD --> ADDITIONAL_INFO

    %% External ETL Data Flow
    GOOGLE_SHEETS --> STAGE2
    STAGE6 --> EXT_SUPABASE
    STAGE7 -.->|"Email Notifications"| EMAIL_SERVICE

    %% Real-time Data Synchronization
    EXT_SUPABASE -.->|"🔄 Real-time Sync<br/>Data Replication"| APP_DB

    %% Data Sources
    GOOGLE_CREDS --> GOOGLE_SHEETS

    %% Click Events for Interactive Navigation
    click MAIN_PAGE "Main_Page.py"
    click HOME_DASH "features/home/views/dashboard.py"
    click AI_CHAT "features/home/views/chatbot.py"
    click DATA_SEARCH "features/home/views/search.py"
    click DATA_UPDATE "features/home/views/update.py"
    click ADMIN_DASH "features/admin/views/dashboard.py"
    click USER_VERIFY "features/admin/views/verify_users.py"
    click RAG_MGMT "features/admin/views/rag.py"
    click USER_SERVICE "core/services/UserService.py"
    click USER_DATA_SERVICE "core/services/UserDataService.py"
    click EMAIL_SERVICE "core/services/EmailService.py"
    click ASSET_SERVICE "core/services/AssetDataService.py"
    click RAG_SERVICE "core/services/RAG.py"
    click GRAPH_BUILD "core/services/agent_graph/build_graph.py"
    click AGENT_BACKEND "core/services/agent_graph/agent_backend.py"
    click SQL_AGENT "core/services/agent_graph/tool_sql_agent.py"
    click RAG_AGENT "core/services/agent_graph/tool_rag.py"
    click VIZ_AGENT "core/services/agent_graph/tool_visualization.py"
    click SEARCH_AGENT "core/services/agent_graph/tool_tavily_search.py"
    click AIRFLOW_TRIGGER "core/services/agent_graph/tool_airflow_trigger.py"
    click INTERNAL_ETL "etl_proces.py"

    %% Styling
    classDef frontend fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    classDef service fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000
    classDef ai fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000
    classDef tool fill:#fff8e1,stroke:#ff8f00,stroke-width:2px,color:#000
    classDef tool_critical fill:#ffebee,stroke:#d32f2f,stroke-width:4px,color:#000
    classDef etl fill:#e8f5e8,stroke:#388e3c,stroke-width:3px,color:#000
    classDef etl_process fill:#f1f8e9,stroke:#689f38,stroke-width:2px,color:#000
    classDef external fill:#fce4ec,stroke:#c2185b,stroke-width:3px,color:#000
    classDef external_etl fill:#e1f5fe,stroke:#0277bd,stroke-width:4px,color:#000
    classDef external_process fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef external_db fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000
    classDef database fill:#e0f2f1,stroke:#00695c,stroke-width:3px,color:#000
    classDef db_table fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,color:#000
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
    class R1,R2,R3,R4,R5,R6,R7,R8,R9,R10 file
    class cInit,mInit,sInit,uInit,aInit,h1,p1,p2,ccss,sConf,sSec file
    class cfg1,cfg2,m1,m2,s1,s2,s3,s4,s5,agInit,ag1,ag2,ag3,ag4,ag5,ag6,ag7,u1,u2,u3,u4,u5,u6,d1,a1,av1,av2,av3,av4,hv1,hv2,hv3,hv4,hv5 img1,img2,img3 file
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
    class R1,R2,R3,R4,R5,R6,R7,R8,R9,R10 file
    class cInit,mInit,sInit,uInit,aInit,h1,p1,p2,ccss,sConf,sSec file
    class cfg1,cfg2,m1,m2,s1,s2,s3,s4,s5,agInit,ag1,ag2,ag3,ag4,ag5,ag6,ag7,u1,u2,u3,u4,u5,u6,d1,a1,av1,av2,av3,av4,hv1,hv2,hv3,hv4,hv5 img1,img2,img3 file
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
