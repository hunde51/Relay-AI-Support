from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.tickets import router as tickets_router
from app.api.knowledge import router as knowledge_router
from app.api.customers import router as customers_router
from app.api.analytics import router as analytics_router
from app.api.settings import router as settings_router
from app.api.agent import router as agent_router
from app.api.ai import router as ai_router
from app.api.dashboard import router as dashboard_router
from app.api.websockets import router as ws_router

app = FastAPI(title="RelayAI Support API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router)
app.include_router(knowledge_router)
app.include_router(customers_router)
app.include_router(analytics_router)
app.include_router(settings_router)
app.include_router(agent_router)
app.include_router(ai_router)
app.include_router(dashboard_router)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"status": "ok"}
