"""RAG with PDF route."""

import asyncio
import uuid
from typing import Optional
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, get_db
from app.dependencies import get_current_active_user
from app.schemas import ResponseItem
from app.utils import get_rag_ollama_response, get_rag_openai_response
from app.utils.rag_vectorstore import load_existing_vectorstore, process_new_pdf
from app.utils.logger import logger

router = APIRouter()


@router.post("/pdf/get/response", response_model=ResponseItem, status_code=200)
async def rag_with_pdf(
    request: Request,
    query: str = Form(...),
    model: str = Form(...),
    past_request_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_active_user),
) -> ResponseItem:
    """Process a PDF with a retrieval-augmented generation flow.

    Either upload a new PDF or query an existing one using past_request_id.
    """
    # Validate model first
    if model not in ["openai", "ollama"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid model."
        )

    # Handle optional PDF file from form data
    form = await request.form()
    pdf_file = form.get("pdf")
    pdf: Optional[UploadFile] = None
    # Check if pdf_file has a filename attribute
    if pdf_file and hasattr(pdf_file, "filename"):
        filename = getattr(pdf_file, "filename", None)
        if filename and filename.strip():
            pdf = pdf_file  # type: ignore[assignment]

    vectorstore: QdrantVectorStore
    current_request_id: str
    tmp_file_path: str | None = None

    # If past_request_id is provided, load existing vectorstore
    if past_request_id:
        if pdf is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot provide both PDF and past_request_id. Use past_request_id to query an existing PDF.",
            )
        vectorstore, current_request_id = await load_existing_vectorstore(
            past_request_id, uuid.UUID(str(_current_user.id)), db
        )
    elif pdf is not None:
        vectorstore, current_request_id, tmp_file_path = await process_new_pdf(
            pdf, uuid.UUID(str(_current_user.id)), db
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either PDF file or request_id must be provided.",
        )

    try:
        # Search for relevant documents filtered by request_id
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="metadata.request_id",
                    match=MatchValue(value=current_request_id),
                )
            ]
        )
        logger.info("Searching with filter for request_id: %s", current_request_id)

        # First, try without filter to see if documents exist
        all_results = await asyncio.to_thread(
            vectorstore.similarity_search,
            query,
            k=5,
        )
        logger.info("Found %s documents without filter", len(all_results))

        if all_results:
            logger.info(
                "Sample document metadata: %s",
                all_results[0].metadata if all_results else "None",
            )

        # Now search with filter
        search_results = await asyncio.to_thread(
            vectorstore.similarity_search,
            query,
            k=5,
            filter=filter_condition,
        )
        logger.info("Found %s documents with request_id filter", len(search_results))

        # If filter returns empty but we have documents, try without filter as fallback
        if not search_results and all_results:
            logger.warning(
                "Filter returned no results, using all documents (filter may not be working correctly)"
            )
            search_results = all_results

        relevant_context = (
            "\n\n".join([doc.page_content for doc in search_results])
            if search_results
            else ""
        )
        # Get response from RAG model using the model specified
        if model == "openai":
            response = get_rag_openai_response(query, relevant_context)
        else:  # model == "ollama"
            response = await get_rag_ollama_response(query, relevant_context)

        return ResponseItem(content=response, request_id=current_request_id)

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
