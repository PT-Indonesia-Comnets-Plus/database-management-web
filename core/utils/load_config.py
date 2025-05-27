"""Configuration management for tools and project settings."""

import os
import yaml
import streamlit as st
from dotenv import load_dotenv
from pyprojroot import here
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class LoadToolsConfig:
    """
    Centralized configuration management for the application.

    This class loads and manages all configuration settings including:
    - Primary agent settings
    - Tavily search configuration  
    - RAG (Retrieval Augmented Generation) settings
    - SQL agent configuration
    - LangSmith tracking settings
    - Memory and graph configurations
    """

    def __init__(self) -> None:
        """Initialize configuration by loading all settings."""
        try:
            self._load_app_config()
            self._load_primary_agent_config()
            self._load_tavily_search_config()
            self._load_rag_config()
            self._load_sqlagent_config()
            self._load_langsmith_config()
            self._load_memory_config()
            self._load_graph_config()
            self._set_environment_variables()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(
                f"Configuration initialization failed: {e}")

    def _load_app_config(self) -> None:
        """Load application configuration from YAML file."""
        try:
            config_path = here("core/configs/tools_configs.yml")
            with open(config_path, "r", encoding='utf-8') as cfg_file:
                self.app_config = yaml.load(cfg_file, Loader=yaml.FullLoader)
            logger.info(f"App config loaded from {config_path}")
        except FileNotFoundError:
            logger.warning(
                f"Configuration file not found at {config_path}, using defaults")
            self.app_config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            self.app_config = {}

    def _set_environment_variables(self) -> None:
        """Set environment variables from dotenv or Streamlit secrets."""
        try:
            # Get API keys with fallback to Streamlit secrets
            self.gemini_api_key = os.getenv(
                "GEMINI_API_KEY") or st.secrets.get("gemini", {}).get("api_key")
            tavily_key = os.getenv("TAVILY_API_KEY") or st.secrets.get(
                "tavily", {}).get("api_key")
            langchain_key = os.getenv("LANGCHAIN_API_KEY") or st.secrets.get(
                "langsmith", {}).get("api_key")

            # Set environment variables
            if tavily_key:
                os.environ["TAVILY_API_KEY"] = tavily_key
                self.tavily_api_key = tavily_key
                logger.info("TAVILY_API_KEY environment variable set")

            if langchain_key:
                os.environ["LANGCHAIN_API_KEY"] = langchain_key
                self.langchain_api_key = langchain_key
                logger.info("LANGCHAIN_API_KEY environment variable set")

            if self.gemini_api_key:
                os.environ["GOOGLE_API_KEY"] = self.gemini_api_key
                logger.info("GOOGLE_API_KEY environment variable set")

            # Set LangSmith environment variables
            if hasattr(self, 'langsmith_tracing') and self.langsmith_tracing:
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                logger.info("LANGCHAIN_TRACING_V2 enabled")

            if hasattr(self, 'langsmith_project_name') and self.langsmith_project_name:
                os.environ["LANGCHAIN_PROJECT"] = self.langsmith_project_name
                logger.info(
                    f"LANGCHAIN_PROJECT set to '{self.langsmith_project_name}'")

        except Exception as e:
            logger.warning(f"Error setting environment variables: {e}")

    def _load_primary_agent_config(self) -> None:
        """Load primary agent configuration."""
        primary_agent = self.app_config.get("primary_agent", {})
        self.primary_agent_llm = primary_agent.get("llm", "gemini-1.5-pro")
        self.primary_agent_llm_temperature = primary_agent.get(
            "llm_temperature", 0.1)

    def _load_tavily_search_config(self) -> None:
        """Load internet search (Tavily) configuration."""
        tavily_config = self.app_config.get("tavily_search_api", {})
        self.tavily_search_max_results = int(
            tavily_config.get("tavily_search_max_results", 5))

    def _load_rag_config(self) -> None:
        """Load Retrieval Augmented Generation (RAG) configuration."""
        rag_config = self.app_config.get("rag_configs", {})
        self.rag_llm = rag_config.get("llm", "gemini-1.5-pro")
        self.rag_llm_temperature = float(
            rag_config.get("llm_temperature", 0.1))
        self.rag_embedding_model = rag_config.get(
            "embedding_model", "models/embedding-001")
        self.rag_unstructured_docs_directory = str(
            here(rag_config.get("unstructured_docs", "docs")))
        self.rag_k = rag_config.get("k", 5)
        self.rag_collection_name = self.app_config.get(
            "rag_configs", {}).get("collection_name", "documents")

    def _load_sqlagent_config(self) -> None:
        """Load SQL Agent configuration."""
        sqlagent_config = self.app_config.get("sqlagent_configs", {})
        self.sql_agent_llm = sqlagent_config.get("llm", "gemini-1.5-pro")
        self.sql_agent_llm_temperature = float(
            sqlagent_config.get("llm_temperature", 0.1))

    def _load_langsmith_config(self) -> None:
        """Load LangSmith tracking configuration."""
        langsmith_config = self.app_config.get("langsmith", {})
        self.langsmith_project_name = langsmith_config.get(
            "project_name", "iconnet-assistant")
        self.langsmith_tracing = langsmith_config.get("tracing", False)

    def _load_memory_config(self) -> None:
        """Load memory directory configuration."""
        memory_config = self.app_config.get("memory", {})
        self.memory_dir = memory_config.get("directory", "memory")

    def _load_graph_config(self) -> None:
        """Load graph configuration."""
        graph_config = self.app_config.get("graph_configs", {})
        self.thread_id = str(graph_config.get("thread_id", "default"))


# Singleton instance for application use
TOOLS_CFG = LoadToolsConfig()
