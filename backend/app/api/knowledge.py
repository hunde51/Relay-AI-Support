from fastapi import APIRouter
from pydantic import BaseModel
from app.services import rag_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@router.post("/ingest-docs")
async def ingest_docs():
    return await rag_service.ingest_documents()


@router.post("/search-knowledge")
async def search_knowledge(body: SearchRequest):
    return await rag_service.search_knowledge(body.query, body.top_k)
