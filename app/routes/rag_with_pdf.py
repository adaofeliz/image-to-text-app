"""RAG with PDF route."""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from app.database import User
from app.dependencies import get_current_active_user
from app.schemas import ResponseItem
from app.utils import get_rag_ollama_response, get_rag_openai_response
from app.utils.logger import logger

router = APIRouter()


@router.post("/pdf/get/response", response_model=ResponseItem, status_code=200)
async def rag_with_pdf(
    pdf: UploadFile = File(...),
    query: str = Form(...),
    model: str = Form(...),
    _current_user: User = Depends(get_current_active_user),
) -> ResponseItem:
    """Process a PDF with a retrieval-augmented generation flow."""
    # Validate model first
    if model not in ["openai", "ollama"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model."
        )

    pdf_content_type = (pdf.content_type or "").lower()
    pdf_filename = (pdf.filename or "").lower()

    if pdf_content_type != "application/pdf" and not pdf_filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a PDF file.",
        )

    tmp_file_path: str | None = None
    vectorstore: QdrantVectorStore | None = None
    collection_name: str | None = None

    try:
        suffix = Path(pdf.filename).suffix if pdf.filename else ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await pdf.read()
            if not content:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The uploaded PDF file is empty.",
                )
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Load the PDF file
        loader = PyPDFLoader(tmp_file_path)
        documents = await asyncio.to_thread(loader.load)

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to extract content from the uploaded PDF.",
            )

        # Split the documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, add_start_index=True
        )
        split_docs = text_splitter.split_documents(documents)

        # Create vector embeddings
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

        collection_name = (
            f"pdf_collection_{pdf_filename}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Create vector store and store embeddings and documents in Qdrant
        vectorstore = await asyncio.to_thread(
            QdrantVectorStore.from_documents,
            split_docs,
            embeddings,
            url="http://qdrant:6333",
            collection_name=collection_name,
        )

        # Search for relevant documents
        search_results = await asyncio.to_thread(vectorstore.similarity_search, query)
        relevant_context = "\n\n".join([doc.page_content for doc in search_results])

        # Get response from RAG model using the model specified
        if model == "openai":
            response = get_rag_openai_response(query, relevant_context)
        else:  # model == "ollama"
            response = get_rag_ollama_response(query, relevant_context)

        return ResponseItem(content=response)

    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to process RAG request: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process the PDF. Please try again later.",
        ) from exc
    finally:
        # Clean up temporary files
        try:
            if tmp_file_path:
                Path(tmp_file_path).unlink(missing_ok=True)
        except Exception as cleanup_exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Unable to remove temporary file %s: %s",
                tmp_file_path or "unknown",
                cleanup_exc,
            )
