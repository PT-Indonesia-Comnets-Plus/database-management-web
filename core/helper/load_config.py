# core/services/agent_graph/load_config.py

import os
import yaml
import streamlit as st
from dotenv import load_dotenv
from pyprojroot import here

load_dotenv()


class LoadToolsConfig:
    """Load configuration for tools and project settings."""

    def __init__(self) -> None:
        self._load_app_config()
        self._set_environment_variables()
        self._load_primary_agent_config()
        self._load_tavily_search_config()
        self._load_rag_config()
        self._load_sqlagent_config()
        self._load_langsmith_config()
        self._load_memory_config()
        self._load_graph_config()

    def _load_app_config(self) -> None:
        """Load application configuration from YAML."""
        config_path = here("configs/tools_configs.yml")
        with open(config_path, "r") as cfg_file:
            self.app_config = yaml.load(cfg_file, Loader=yaml.FullLoader)

    def _set_environment_variables(self) -> None:
        """Set environment variables from dotenv or Streamlit secrets."""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", st.secrets.get(
            "gemini", {}).get("api_key"))
        self.tavily_api_key = os.environ["TAVILY_API_KEY"] = os.getenv(
            "TAVILY_API_KEY") or st.secrets.get(["tavily"]["api_key"])
        self.langchain_api_key = os.environ["LANGCHAIN_API_KEY"] = os.getenv(
            "LANGCHAIN_API_KEY") or st.secrets.get(["langsmith"]["api_key"])

        if self.gemini_api_key:
            os.environ["GOOGLE_API_KEY"] = self.gemini_api_key
            print("🔑 GOOGLE_API_KEY environment variable set from GEMINI_API_KEY.")
        else:
            print(
                "⚠️ GEMINI_API_KEY not found. langchain-google-genai might fall back to ADC.")

    def _load_primary_agent_config(self) -> None:
        """Load primary agent configuration."""
        primary_agent = self.app_config.get("primary_agent", {})
        self.primary_agent_llm = primary_agent.get("llm")
        self.primary_agent_llm_temperature = primary_agent.get(
            "llm_temperature")

    def _load_tavily_search_config(self) -> None:
        """Load internet search (Tavily) configuration."""
        tavily_config = self.app_config.get("tavily_search_api", {})
        self.tavily_search_max_results = int(
            tavily_config.get("tavily_search_max_results", 0))

    def _load_rag_config(self) -> None:
        """Load Retrieval Augmented Generation (RAG) configuration."""
        rag_config = self.app_config.get("rag_configs", {})
        self.rag_llm = rag_config.get("llm")
        self.rag_llm_temperature = float(rag_config.get("llm_temperature", 0))
        self.rag_embedding_model = rag_config.get("embedding_model")
        self.rag_unstructured_docs_directory = str(
            here(rag_config.get("unstructured_docs", "")))
        self.rag_k = rag_config.get("k")
        self.rag_collection_name = self.app_config.get(
            "srag_configs", {}).get("collection_name")

    def _load_sqlagent_config(self) -> None:
        """Load SQL Agent configuration."""
        sqlagent_config = self.app_config.get("sqlagent_configs", {})
        self.sql_agent_llm = sqlagent_config.get("llm")
        self.sql_agent_llm_temperature = float(
            sqlagent_config.get("llm_temperature"))

    def _load_langsmith_config(self) -> None:
        """Load LangSmith tracking configuration."""
        langsmith_config = self.app_config.get("langsmith", {})
        self.langsmith_project_name = langsmith_config.get("project_name")
        self.langsmith_tracing = langsmith_config.get("tracing")

    def _load_memory_config(self) -> None:
        """Load memory directory configuration."""
        memory_config = self.app_config.get("memory", {})
        self.memory_dir = memory_config.get("directory")

    def _load_graph_config(self) -> None:
        """Load graph configuration."""
        graph_config = self.app_config.get("graph_configs", {})
        self.thread_id = str(graph_config.get("thread_id"))


# Instance for use
TOOLS_CFG = LoadToolsConfig()
