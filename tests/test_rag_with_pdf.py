"""Tests for RAG with PDF routes."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
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
        data={"query": "What is this about?"},
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
        data={"query": "What is this about?"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid" in data["detail"].lower() or "pdf" in data["detail"].lower()


@pytest.mark.asyncio
async def test_rag_with_pdf_empty_file(client: AsyncClient, authenticated_user: dict):
    """Test RAG with PDF using empty file."""
    empty_file = BytesIO(b"")

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("empty.pdf", empty_file, "application/pdf")},
        data={"query": "What is this about?"},
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
        data={"query": "What is this about?"},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 422


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
@patch("app.routes.rag_with_pdf.QdrantVectorStore")
@patch("app.routes.rag_with_pdf.OpenAIEmbeddings")
@patch("app.routes.rag_with_pdf.RecursiveCharacterTextSplitter")
@patch("app.routes.rag_with_pdf.PyPDFLoader")
async def test_rag_with_pdf_success(
    mock_pdf_loader,
    mock_text_splitter,
    mock_embeddings,
    mock_qdrant_store,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test successful RAG with PDF processing."""
    # Mock PDF loader
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_pdf_loader.return_value = mock_loader_instance

    # Mock text splitter
    mock_splitter_instance = MagicMock()
    mock_splitter_instance.split_documents.return_value = [mock_doc]
    mock_text_splitter.return_value = mock_splitter_instance

    # Mock embeddings
    mock_embeddings_instance = MagicMock()
    mock_embeddings.return_value = mock_embeddings_instance

    # Mock Qdrant vector store
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]
    mock_qdrant_store.from_documents = MagicMock(return_value=mock_vectorstore)

    # Mock OpenAI response
    mock_openai_response.return_value = "This is the answer based on the PDF content"

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert data["content"] == "This is the answer based on the PDF content"


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.PyPDFLoader")
async def test_rag_with_pdf_empty_extraction(
    mock_pdf_loader,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when PDF extraction returns empty."""
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = []
    mock_pdf_loader.return_value = mock_loader_instance

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "extract" in data["detail"].lower() or "content" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.QdrantVectorStore")
@patch("app.routes.rag_with_pdf.OpenAIEmbeddings")
@patch("app.routes.rag_with_pdf.RecursiveCharacterTextSplitter")
@patch("app.routes.rag_with_pdf.PyPDFLoader")
async def test_rag_with_pdf_qdrant_error(
    mock_pdf_loader,
    mock_text_splitter,
    mock_embeddings,
    mock_qdrant_store,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when Qdrant connection fails."""
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_pdf_loader.return_value = mock_loader_instance

    mock_splitter_instance = MagicMock()
    mock_splitter_instance.split_documents.return_value = [mock_doc]
    mock_text_splitter.return_value = mock_splitter_instance

    mock_embeddings.return_value = MagicMock()

    mock_qdrant_store.from_documents.side_effect = Exception("Qdrant connection failed")

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?"},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "failed" in data["detail"].lower()


@pytest.mark.asyncio
@patch("app.routes.rag_with_pdf.get_rag_openai_response")
@patch("app.routes.rag_with_pdf.QdrantVectorStore")
@patch("app.routes.rag_with_pdf.OpenAIEmbeddings")
@patch("app.routes.rag_with_pdf.RecursiveCharacterTextSplitter")
@patch("app.routes.rag_with_pdf.PyPDFLoader")
async def test_rag_with_pdf_openai_error(
    mock_pdf_loader,
    mock_text_splitter,
    mock_embeddings,
    mock_qdrant_store,
    mock_openai_response,
    client: AsyncClient,
    authenticated_user: dict,
):
    """Test RAG with PDF when OpenAI API fails."""
    mock_doc = MagicMock()
    mock_doc.page_content = "Sample PDF content"
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_pdf_loader.return_value = mock_loader_instance

    mock_splitter_instance = MagicMock()
    mock_splitter_instance.split_documents.return_value = [mock_doc]
    mock_text_splitter.return_value = mock_splitter_instance

    mock_embeddings.return_value = MagicMock()

    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = [mock_doc]
    mock_qdrant_store.from_documents = MagicMock(return_value=mock_vectorstore)

    mock_openai_response.side_effect = Exception("OpenAI API error")

    pdf_content = b"%PDF-1.4\nfake pdf content"
    pdf_file = BytesIO(pdf_content)

    response = await client.post(
        "/pdf/get/response",
        files={"pdf": ("test.pdf", pdf_file, "application/pdf")},
        data={"query": "What is this about?"},
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
        data={"query": "What is this about?"},
        headers=headers,
    )

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "verified" in data["detail"].lower()
