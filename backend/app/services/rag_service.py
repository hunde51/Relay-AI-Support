import hashlib
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_engine.vector_store import get_vector_store
from app.db.models import KnowledgeChunkORM

DOCS_DIR = Path(__file__).parents[1] / "ai_engine" / "sample_docs"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def ingest_documents() -> dict:
    """Ingest built-in sample docs (no DB chunk tracking — seed only)."""
    docs = []
    for file in DOCS_DIR.glob("*.txt"):
        text = file.read_text()
        chunks = splitter.create_documents([text], metadatas=[{"source": file.name}])
        docs.extend(chunks)

    store = get_vector_store()
    store.add_documents(docs)
    return {"ingested": len(docs), "sources": [f.name for f in DOCS_DIR.glob("*.txt")]}


async def ingest_document_file(
    db: AsyncSession,
    storage_path: str | None,
    title: str,
    document_id: str,
    organization_id: str,
    source_name: str = "",
) -> dict:
    """
    Ingest a single uploaded document file.
    - Chunks the text
    - Skips chunks whose content_hash already exists in knowledge_chunks (dedup)
    - Stores each new chunk in Qdrant with chunk_id as point payload
    - Stores each new chunk in knowledge_chunks table
    """
    if not storage_path or not Path(storage_path).exists():
        raise FileNotFoundError(f"File not found: {storage_path}")

    text = Path(storage_path).read_text(errors="replace")
    raw_chunks = splitter.split_text(text)

    # Load existing hashes for this document to avoid re-ingesting unchanged chunks
    existing_hashes_result = await db.execute(
        select(KnowledgeChunkORM.content_hash).where(
            KnowledgeChunkORM.document_id == document_id
        )
    )
    existing_hashes = {row[0] for row in existing_hashes_result.all()}

    store = get_vector_store()
    new_chunks = []
    orm_chunks = []

    for idx, chunk_text in enumerate(raw_chunks):
        content_hash = _content_hash(chunk_text)
        if content_hash in existing_hashes:
            continue  # skip unchanged chunk

        chunk_id = f"{document_id}-{idx}"
        new_chunks.append(
            (
                chunk_id,
                chunk_text,
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "organization_id": organization_id,
                    "source": source_name or title,
                    "chunk_index": idx,
                },
            )
        )
        orm_chunks.append(
            KnowledgeChunkORM(
                id=chunk_id,
                organization_id=organization_id,
                document_id=document_id,
                chunk_index=str(idx),
                content=chunk_text,
                content_hash=content_hash,
                token_count=str(len(chunk_text.split())),
                embedding_id=chunk_id,
                metadata_json={"source": source_name or title},
            )
        )

    if new_chunks:
        from langchain_core.documents import Document

        lc_docs = [
            Document(page_content=text, metadata=meta)
            for _, text, meta in new_chunks
        ]
        store.add_documents(lc_docs)

        for orm in orm_chunks:
            db.add(orm)
        # caller commits

    return {
        "ingested": len(new_chunks),
        "skipped": len(raw_chunks) - len(new_chunks),
        "document_id": document_id,
    }


async def search_knowledge(
    query: str,
    top_k: int = 4,
    organization_id: str | None = None,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Vector similarity search.
    Returns results with chunk_id, document_id, source, content, score.
    Filters by organization_id and optionally source via Qdrant payload filter.
    """
    store = get_vector_store()

    # Build Qdrant filter if needed
    filter_obj = None
    if organization_id or source_filter:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Must

        conditions = []
        if organization_id:
            conditions.append(
                FieldCondition(key="organization_id", match=MatchValue(value=organization_id))
            )
        if source_filter:
            conditions.append(
                FieldCondition(key="source", match=MatchValue(value=source_filter))
            )
        filter_obj = Filter(must=conditions)

    results = store.similarity_search_with_score(query, k=top_k, filter=filter_obj)

    return [
        {
            "chunk_id": doc.metadata.get("chunk_id"),
            "document_id": doc.metadata.get("document_id"),
            "source": doc.metadata.get("source"),
            "content": doc.page_content,
            "score": round(float(score), 4),
        }
        for doc, score in results
    ]
