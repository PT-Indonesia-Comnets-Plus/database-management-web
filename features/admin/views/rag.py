import streamlit as st
# Import RAGService for type hinting
from core.services.RAG import RAGService


def app(rag_service: RAGService):
    """
    Provides an interface for administrators to upload PDF documents
    to be processed and added to the RAG knowledge base.

    Args:
        rag_service: An instance of RAGService to handle PDF processing.
    """
    st.title("📚 RAG Document Management")  # features/admin/views/rag2.py

    st.markdown("Upload PDF files to update the internal knowledge base.")

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload a PDF document",
        type=["pdf"],
        accept_multiple_files=False,  # Process one file at a time for clarity
        key="rag_pdf_uploader"
    )

    if uploaded_file is not None:
        st.subheader(f"Preview: {uploaded_file.name}")

        rag_service.display_pdf_preview(uploaded_file)

        st.subheader("Processing Options")
        if st.button(f"🚀 Process and Add '{uploaded_file.name}' to Knowledge Base"):
            with st.spinner(f"Processing {uploaded_file.name}... This may take a few moments."):
                success = rag_service.process_uploaded_pdf(uploaded_file)
            if success:
                st.success(
                    f"File '{uploaded_file.name}' processed successfully!")
            else:
                st.error("Processing failed. Please check the logs or try again.")
    else:
        st.info("Upload a PDF file to begin.")


# Note: The main execution block `if __name__ == "__main__":` is usually
# not needed for view files called by a controller. Remove it if present.
