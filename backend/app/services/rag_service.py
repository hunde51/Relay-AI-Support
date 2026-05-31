from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.ai_engine.vector_store import get_vector_store

DOCS_DIR = Path(__file__).parents[1] / "ai_engine" / "sample_docs"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


async def ingest_documents() -> dict:
    """Ingest built-in sample docs."""
    docs = []
    for file in DOCS_DIR.glob("*.txt"):
        text = file.read_text()
        chunks = splitter.create_documents([text], metadatas=[{"source": file.name}])
        docs.extend(chunks)

    store = get_vector_store()
    store.add_documents(docs)
    return {"ingested": len(docs), "sources": [f.name for f in DOCS_DIR.glob("*.txt")]}


async def ingest_document_file(storage_path: str | None, title: str, document_id: str) -> dict:
    """Ingest a single uploaded document file."""
    if not storage_path or not Path(storage_path).exists():
        raise FileNotFoundError(f"File not found: {storage_path}")

    text = Path(storage_path).read_text(errors="replace")
    chunks = splitter.create_documents(
        [text],
        metadatas=[{"source": title, "document_id": document_id}],
    )

    store = get_vector_store()
    store.add_documents(chunks)
    return {"ingested": len(chunks), "document_id": document_id}


async def search_knowledge(query: str, top_k: int = 4) -> list[dict]:
    store = get_vector_store()
    results = store.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source"),
            "document_id": doc.metadata.get("document_id"),
            "score": round(float(score), 4),
        }
        for doc, score in results
    ]
