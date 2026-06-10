from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.agent import router as agent_router
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.api_keys import router as api_keys_router
from app.api.auth import router as auth_router
from app.api.customers import router as customers_router
from app.api.dashboard import router as dashboard_router
from app.api.external import router as external_router
from app.api.knowledge import router as knowledge_router
from app.api.notifications import router as notifications_router
from app.api.settings import router as settings_router
from app.api.tickets import router as tickets_router
from app.api.webhooks import router as webhooks_router
from app.api.websockets import router as ws_router
from app.core.middleware import AuthMiddleware, StructuredErrorMiddleware, RateLimitMiddleware

app = FastAPI(title="RelayAI Support API")

@app.get("/")
def root():
    return {
        "message": "RelayAI Support API is running",
        "docs": "/docs",
        "health": "/health"
    }

app.add_middleware(AuthMiddleware)
app.add_middleware(StructuredErrorMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

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
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(ws_router)
app.include_router(api_keys_router)
app.include_router(external_router)
app.include_router(webhooks_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except Exception:
        return {"error": "metrics_unavailable"}
