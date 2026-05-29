from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.tickets import router as tickets_router
from app.api.knowledge import router as knowledge_router
from app.api.agent import router as agent_router
from app.api.websockets import router as ws_router

app = FastAPI(title="RelayAI Support API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(agent_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}
