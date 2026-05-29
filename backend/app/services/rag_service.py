from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.ai_engine.vector_store import get_vector_store

DOCS_DIR = Path(__file__).parent / "sample_docs"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


async def ingest_documents() -> dict:
    docs = []
    for file in DOCS_DIR.glob("*.txt"):
        text = file.read_text()
        chunks = splitter.create_documents([text], metadatas=[{"source": file.name}])
        docs.extend(chunks)

    store = get_vector_store()
    store.add_documents(docs)
    return {"ingested": len(docs), "sources": [f.name for f in DOCS_DIR.glob("*.txt")]}


async def search_knowledge(query: str, top_k: int = 4) -> list[dict]:
    store = get_vector_store()
    results = store.similarity_search_with_score(query, k=top_k)
    return [
        {"content": doc.page_content, "source": doc.metadata.get("source"), "score": round(float(score), 4)}
        for doc, score in results
    ]
