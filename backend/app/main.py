from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from fastapi.responses import HTMLResponse

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
from app.api.email_integration import router as email_router
from app.api.widget import router as widget_router
from app.api.invitations import router as invitations_router
from app.api.usage import router as usage_router
from app.api.stripe_webhook import router as stripe_router
from app.core.middleware import AuthMiddleware, StructuredLogMiddleware, RateLimitMiddleware, UsageTrackingMiddleware
from app.core.metrics import request_duration
import time

app = FastAPI(title="RelayAI Support API")

@app.get("/")
def root():
    return {
        "message": "RelayAI Support API is running",
        "docs": "/docs",
        "health": "/health"
    }

app.add_middleware(AuthMiddleware)
app.add_middleware(UsageTrackingMiddleware)
app.add_middleware(StructuredLogMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)


@app.middleware("http")
async def _prometheus_duration(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    request_duration.observe(time.monotonic() - start)
    return response

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
app.include_router(email_router)
app.include_router(widget_router)
app.include_router(invitations_router)
app.include_router(usage_router)
app.include_router(stripe_router)

_WIDGET_JS = (Path(__file__).resolve().parent / "widget_script" / "widget.js").read_text()


@app.get("/widget.js", response_class=HTMLResponse, include_in_schema=False)
async def serve_widget_js():
    return HTMLResponse(_WIDGET_JS, media_type="application/javascript")


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
