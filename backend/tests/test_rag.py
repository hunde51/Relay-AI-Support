import pytest
from unittest.mock import MagicMock, patch

from app.ai_engine.vector_store import get_embeddings, VECTOR_SIZE
from app.services.rag_service import _content_hash, search_knowledge


class TestEmbeddingModel:
    def test_embedding_model_is_text_embedding_004(self):
        embeddings = get_embeddings()
        assert embeddings.model == "models/text-embedding-004"

    def test_vector_size_is_768(self):
        assert VECTOR_SIZE == 768


class TestContentHash:
    def test_content_hash_sha256(self):
        h = _content_hash("hello world")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_content_hash_deterministic(self):
        assert _content_hash("same text") == _content_hash("same text")

    def test_content_hash_differs(self):
        assert _content_hash("foo") != _content_hash("bar")


@pytest.mark.asyncio
async def test_search_knowledge_filters_by_org():
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = []

    with patch("app.services.rag_service.get_vector_store", return_value=mock_store):
        results = await search_knowledge(
            query="test query",
            top_k=4,
            organization_id="org-123",
        )

    assert results == []
    call_args = mock_store.similarity_search_with_score.call_args
    assert call_args is not None
    filter_obj = call_args.kwargs.get("filter")
    assert filter_obj is not None
    conditions = filter_obj.must
    assert any(c.key == "organization_id" and c.match.value == "org-123" for c in conditions)


@pytest.mark.asyncio
async def test_search_knowledge_applies_score_threshold():
    from langchain_core.documents import Document

    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = [
        (Document(page_content="low relevance", metadata={"chunk_id": "c1", "source": "s1", "organization_id": "org-1"}), 0.3),
        (Document(page_content="high relevance", metadata={"chunk_id": "c2", "source": "s2", "organization_id": "org-1"}), 0.85),
        (Document(page_content="medium relevance", metadata={"chunk_id": "c3", "source": "s3", "organization_id": "org-1"}), 0.6),
    ]

    with patch("app.services.rag_service.get_vector_store", return_value=mock_store):
        results = await search_knowledge(
            query="test",
            organization_id="org-1",
            score_threshold=0.5,
        )

    assert len(results) == 2
    scores = [r["score"] for r in results]
    assert all(s >= 0.5 for s in scores)
    assert results[0]["chunk_id"] == "c2"
    assert results[1]["chunk_id"] == "c3"


@pytest.mark.asyncio
async def test_search_knowledge_no_org_no_filter():
    mock_store = MagicMock()
    mock_store.similarity_search_with_score.return_value = []

    with patch("app.services.rag_service.get_vector_store", return_value=mock_store):
        results = await search_knowledge(query="test")

    assert results == []
    call_args = mock_store.similarity_search_with_score.call_args
    assert call_args is not None
    assert call_args.kwargs.get("filter") is None


class TestJobModelTracking:
    def test_ingestion_job_has_tracking_fields(self):
        from app.models.knowledge import KnowledgeIngestionJobORM
        cols = {c.name: c for c in KnowledgeIngestionJobORM.__table__.columns}
        assert "chunks_created" in cols
        assert "started_at" in cols
        assert "completed_at" in cols
        assert cols["chunks_created"].type.python_type is int

    def test_knowledge_document_has_checksum(self):
        from app.models.knowledge import KnowledgeDocumentORM
        cols = {c.name: c for c in KnowledgeDocumentORM.__table__.columns}
        assert "checksum" in cols

    def test_ai_response_has_citations(self):
        from app.models.ai import AIResponseORM
        cols = {c.name: c for c in AIResponseORM.__table__.columns}
        assert "citations" in cols


class TestChecksumSkip:
    def test_upload_creates_doc_with_checksum(self, client):
        resp = client.post("/knowledge/documents/upload", files={"file": ("test.txt", b"hello world")})
        assert resp.status_code == 201
        data = resp.json()
        assert "checksum" in data
        assert data["checksum"] == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_reingest_same_file_checksum_skip(self, client, monkeypatch):
        # Mock the actual ingestion so we don"t need Qdrant
        async def mock_ingest(*args, **kwargs):
            return {"ingested": 1, "skipped": 0, "document_id": args[3] if len(args) > 3 else kwargs.get("document_id", "doc-1")}
        monkeypatch.setattr("app.services.rag_service.ingest_document_file", mock_ingest)

        # Create a source to reuse
        src = client.post("/knowledge/sources", params={"name": "ChecksumTest", "source_type": "manual_upload"})
        assert src.status_code == 201
        source_id = src.json()["id"]

        # Upload once with this source
        r1 = client.post("/knowledge/documents/upload", params={"source_id": source_id}, files={"file": ("test.txt", b"hello world")})
        assert r1.status_code == 201
        doc_id1 = r1.json()["id"]

        # Ingest it — succeeds
        r_ingest = client.post(f"/knowledge/documents/{doc_id1}/ingest")
        assert r_ingest.status_code == 200

        # Upload same content again with the same source
        r2 = client.post("/knowledge/documents/upload", params={"source_id": source_id}, files={"file": ("test2.txt", b"hello world")})
        assert r2.status_code == 201
        doc_id2 = r2.json()["id"]

        # Ingest again — should be skipped due to checksum match (same source_id + checksum)
        r_skip = client.post(f"/knowledge/documents/{doc_id2}/ingest")
        assert r_skip.status_code == 200
        assert r_skip.json().get("skipped") is True


class TestCitationsAPI:
    def test_get_run_includes_citations(self, client):
        # Create a ticket
        r = client.post("/tickets", json={"title": "Citation test", "message": "test"})
        assert r.status_code == 201
        ticket_id = r.json()["id"]

        # Run AI
        r_run = client.post(f"/ai/tickets/{ticket_id}/run")
        assert r_run.status_code == 200
        run_id = r_run.json()["run_id"]

        # Get run
        r_get = client.get(f"/ai/runs/{run_id}")
        assert r_get.status_code == 200
        data = r_get.json()
        assert "citations" in data
