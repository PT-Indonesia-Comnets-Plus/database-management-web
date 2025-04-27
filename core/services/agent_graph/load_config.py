
import os
import yaml
from dotenv import load_dotenv
from pyprojroot import here

load_dotenv()


class LoadToolsConfig:

    def __init__(self) -> None:
        with open(here(r"configs\tools_configs.yml")) as cfg:
            app_config = yaml.load(cfg, Loader=yaml.FullLoader)

        # Set environment variables
        os.environ['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")
        os.environ['TAVILY_API_KEY'] = os.getenv("TAVILY_API_KEY")

        # Primary agent
        self.primary_agent_llm = app_config["primary_agent"]["llm"]
        self.primary_agent_llm_temperature = app_config["primary_agent"]["llm_temperature"]

        # Internet Search config
        self.tavily_search_max_results = int(
            app_config["tavily_search_api"]["tavily_search_max_results"])

        # Swiss Airline Policy RAG configs
        self.policy_rag_llm = app_config["pdf_rag"]["llm"]
        self.policy_rag_llm_temperature = float(
            app_config["pdf_rag"]["llm_temperature"])
        self.policy_rag_embedding_model = app_config["pdf_rag"]["embedding_model"]
        self.policy_rag_vectordb_directory = str(here(
            app_config["pdf_rag"]["vectordb"]))  # needs to be strin for summation in chromadb backend: self._settings.require("persist_directory") + "/chroma.sqlite3"
        self.policy_rag_unstructured_docs_directory = str(here(
            app_config["pdf_rag"]["unstructured_docs"]))
        self.policy_rag_k = app_config["pdf_rag"]["k"]
        self.policy_rag_chunk_size = app_config["pdf_rag"]["chunk_size"]
        self.policy_rag_chunk_overlap = app_config["pdf_rag"]["chunk_overlap"]
        self.policy_rag_collection_name = app_config["pdf_rag"]["collection_name"]

        # Travel SQL Agent configs
        self.travel_sqldb_directory = str(here(
            app_config["sqlagent_configs"]["sqldb_dir"]))
        self.travel_sqlagent_llm = app_config["sqlagent_configs"]["llm"]
        self.travel_sqlagent_llm_temperature = float(
            app_config["sqlagent_configs"]["llm_temperature"])

        # Graph configs
        self.thread_id = str(
            app_config["graph_configs"]["thread_id"])
