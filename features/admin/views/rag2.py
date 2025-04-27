import os
import yaml
from pyprojroot import here
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class PrepareVectorDB:
    """
    A class to prepare and manage a Vector Database (VectorDB) using documents from a specified directory.
    The class performs the following tasks:
    - Loads and splits documents (PDFs).
    - Splits the text into chunks based on the specified chunk size and overlap.
    - Embeds the document chunks using a specified embedding model.
    - Stores the embedded vectors in a persistent VectorDB directory.
    """

    def __init__(self,
                 doc_dir: str,
                 chunk_size: int,
                 chunk_overlap: int,
                 embedding_model: str,
                 vectordb_dir: str,
                 collection_name: str
                 ) -> None:

        self.doc_dir = doc_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.vectordb_dir = vectordb_dir
        self.collection_name = collection_name

    def path_maker(self, file_name: str, doc_dir):
        """
        Creates a full file path by joining the provided directory and file name.
        """
        return os.path.join(here(doc_dir), file_name)

    def run(self):
        """
        Executes the main logic to create and store document embeddings in a VectorDB.
        """
        if not os.path.exists(here(self.vectordb_dir)):
            # If it doesn't exist, create the directory and create the embeddings
            os.makedirs(here(self.vectordb_dir))
            print(f"Directory '{self.vectordb_dir}' was created.")

            file_list = os.listdir(here(self.doc_dir))
            docs = [PyPDFLoader(self.path_maker(
                fn, self.doc_dir)).load_and_split() for fn in file_list]
            docs_list = [item for sublist in docs for item in sublist]

            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
            )
            doc_splits = text_splitter.split_documents(docs_list)

            # Add to vectorDB using Gemini embeddings
            vectordb = Chroma.from_documents(
                documents=doc_splits,
                collection_name=self.collection_name,
                embedding=GoogleGenerativeAIEmbeddings(
                    model=self.embedding_model),
                persist_directory=str(here(self.vectordb_dir))
            )
            print("VectorDB is created and saved.")
            print("Number of vectors in vectordb:",
                  vectordb._collection.count(), "\n\n")
        else:
            print(f"Directory '{self.vectordb_dir}' already exists.")


if __name__ == "__main__":
    with open(here("configs/tools_config.yml")) as cfg:
        app_config = yaml.load(cfg, Loader=yaml.FullLoader)

    # Uncomment the following configs to run for swiss airline policy document
    chunk_size = app_config["pdf_rag"]["chunk_size"]
    chunk_overlap = app_config["pdf_rag"]["chunk_overlap"]
    embedding_model = app_config["pdf_rag"]["embedding_model"]
    vectordb_dir = app_config["pdf_rag"]["vectordb"]
    collection_name = app_config["pdf_rag"]["collection_name"]
    doc_dir = app_config["pdf_rag"]["unstructured_docs"]

    prepare_db_instance = PrepareVectorDB(
        doc_dir=doc_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        vectordb_dir=vectordb_dir,
        collection_name=collection_name)

    prepare_db_instance.run()

    # Uncomment the following configs to run for stories document
    chunk_size = app_config["stories_rag"]["chunk_size"]
    chunk_overlap = app_config["stories_rag"]["chunk_overlap"]
    embedding_model = app_config["stories_rag"]["embedding_model"]
    vectordb_dir = app_config["stories_rag"]["vectordb"]
    collection_name = app_config["stories_rag"]["collection_name"]
    doc_dir = app_config["stories_rag"]["unstructured_docs"]

    prepare_db_instance = PrepareVectorDB(
        doc_dir=doc_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
        vectordb_dir=vectordb_dir,
        collection_name=collection_name)

    prepare_db_instance.run()
