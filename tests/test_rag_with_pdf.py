"""Tests for RAG with PDF routes."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from app.database.models import User
from app.utils import create_access_token, get_password_hash


@pytest.mark.asyncio
async def test_rag_with_pdf_unauthorized(client: AsyncClient):
    """Test RAG with PDF without authentication."""
    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rag_with_pdf_invalid_file_type(
    client: AsyncClient, authenticated_user: dict
):
    """Test RAG with PDF using invalid file type."""
    text_file = BytesIO(b"This is not a PDF")

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.txt", text_file, "text/plain")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower() or "pdf" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_empty_file(
    mock_process_new_pdf,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF using empty file."""
    # Mock process_new_pdf to raise HTTPException for empty file
    mock_process_new_pdf.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="The uploaded PDF file is empty.",
    )

    empty_file = BytesIO(b"")

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("empty.pdf", empty_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "empty" in data["detail"].lower()


@pytest.mark.asyncio
async def test_rag_with_pdf_missing_file(client: AsyncClient, authenticated_user: dict):
    """Test RAG with PDF without file."""
    response = await client.post(
        "/pdf/get/response",
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )
    # Route returns 400 when neither PDF nor past_request_id is provided
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert (
        "either" in data["detail"].lower()
        or "must be provided" in data["detail"].lower()
    )


@pytest.mark.asyncio
async def test_rag_with_pdf_missing_query(
    client: AsyncClient, authenticated_user: dict
):
    """Test RAG with PDF without query parameter."""
    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_openai_response")
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_success(
    mock_process_new_pdf,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test successful RAG with PDF processing."""
    # Mock document
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_doc.metadata = {"request_id": "test-request-id"}

    # Mock vectorstore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]

    # Mock process_new_pdf utility function
    mock_process_new_pdf.return_value = (
        mock_vectorstore,
        "test-request-id",
        "/tmp/test.pdf",
    )

    # Mock OpenAI response
    mock_openai_response.return_value = "This is the answer based on the PDF content"

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "request_id" in data
    assert data["content"] == "This is the answer based on the PDF content"
    assert data["request_id"] == "test-request-id"


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_empty_extraction(
    mock_process_new_pdf,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when PDF extraction returns empty."""
    # Mock process_new_pdf to raise HTTPException for empty extraction
    mock_process_new_pdf.side_effect = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unable to extract content from the uploaded PDF.",
    )

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "extract" in data["detail"].lower() or "content" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_qdrant_error(
    mock_process_new_pdf,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when Qdrant connection fails."""
    # Mock process_new_pdf to raise HTTPException for Qdrant error
    mock_process_new_pdf.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to process the PDF. Please try again later.",
    )

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_openai_response")
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_openai_error(
    mock_process_new_pdf,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when OpenAI API fails."""
    # Mock document
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_doc.metadata = {"request_id": "test-request-id"}

    # Mock vectorstore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]

    # Mock process_new_pdf utility function
    mock_process_new_pdf.return_value = (
        mock_vectorstore,
        "test-request-id",
        "/tmp/test.pdf",
    )

    # Mock OpenAI response to raise exception
    mock_openai_response.side_effect = Exception("OpenAI API error")

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_rag_with_pdf_unverified_user(
    client: AsyncClient, db_session, test_user_data
):
    """Test RAG with PDF with unverified user."""
    user = User(
        name=test_user_data["name"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_verified=False,
        verification_token=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {access_token}"}

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=headers,
    )

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "verified" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_openai_response")
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_model_selection_openai(
    mock_process_new_pdf,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test that OpenAI model is selected when model='openai'."""
    # Mock document
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_doc.metadata = {"request_id": "test-request-id"}

    # Mock vectorstore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]

    # Mock process_new_pdf utility function
    mock_process_new_pdf.return_value = (
        mock_vectorstore,
        "test-request-id",
        "/tmp/test.pdf",
    )

    mock_openai_response.return_value = "OpenAI response"

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "openai"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    mock_openai_response.assert_called_once()
    data = response.json()
    assert data["content"] == "OpenAI response"
    assert data["request_id"] == "test-request-id"


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_ollama_response")
@patch("app.routes.rag_with_pdf.process_new_pdf")
async def test_rag_with_pdf_model_selection_ollama(
    mock_process_new_pdf,
    mock_ollama_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test that Ollama model is selected when model='ollama'."""
    # Mock document
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_doc.metadata = {"request_id": "test-request-id"}

    # Mock vectorstore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]

    # Mock process_new_pdf utility function
    mock_process_new_pdf.return_value = (
        mock_vectorstore,
        "test-request-id",
        "/tmp/test.pdf",
    )

    # Mock async function
    async def async_mock(*_args, **_kwargs):
        return "Ollama response"

    mock_ollama_response.side_effect = async_mock

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "ollama"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    mock_ollama_response.assert_called_once()
    data = response.json()
    assert data["content"] == "Ollama response"
    assert data["request_id"] == "test-request-id"


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_openai_response")
@patch("app.routes.rag_with_pdf.load_existing_vectorstore")
async def test_rag_with_pdf_past_request_id(
    mock_load_existing_vectorstore,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF using past_request_id."""
    # Mock document
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content from past request"
    mock_doc.metadata = {"request_id": "past-request-id"}

    # Mock vectorstore
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]

    # Mock load_existing_vectorstore utility function
    mock_load_existing_vectorstore.return_value = (
        mock_vectorstore,
        "past-request-id",
    )

    mock_openai_response.return_value = "Response from past PDF"

    response = await client.post(
        "/pdf/get/response",
        data={
            "query": "What is this about?",
            "model": "openai",
            "past_request_id": "past-request-id",
        },
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "request_id" in data
    assert data["content"] == "Response from past PDF"
    assert data["request_id"] == "past-request-id"
    mock_load_existing_vectorstore.assert_called_once()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.load_existing_vectorstore")
async def test_rag_with_pdf_past_request_id_not_found(
    mock_load_existing_vectorstore,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when past_request_id is not found."""

    # Mock load_existing_vectorstore to raise HTTPException
    mock_load_existing_vectorstore.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Request ID 'invalid-id' not found or you don't have access to it.",
    )

    response = await client.post(
        "/pdf/get/response",
        data={
            "query": "What is this about?",
            "model": "openai",
            "past_request_id": "invalid-id",
        },
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.load_existing_vectorstore")
async def test_rag_with_pdf_both_pdf_and_past_request_id(
    mock_load_existing_vectorstore,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when both PDF and past_request_id are provided."""
    # Mock vectorstore to avoid 404
    mock_vectorstore = MagicMock()
    mock_load_existing_vectorstore.return_value = (mock_vectorstore, "some-id")

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)
    pdf_file.seek(0)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={
            "query": "What is this about?",
            "model": "openai",
            "past_request_id": "some-id",
        },
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "both" in data["detail"].lower() or "cannot" in data["detail"].lower()


@pytest.mark.asyncio
async def test_rag_with_pdf_invalid_model(
    client: AsyncClient, authenticated_user: dict
):
    """Test RAG with PDF with invalid model parameter."""
    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?", "model": "invalid-model"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower() or "model" in data["detail"].lower()
