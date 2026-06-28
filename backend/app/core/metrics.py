"""Prometheus metrics for RelayAI.

All metrics are registered at import time.  The /metrics endpoint in main.py
calls generate_latest() which collects everything automatically.
"""
from prometheus_client import Counter, Gauge, Histogram

ai_runs_total = Counter("relayai_ai_runs_total", "Total AI runs", ["status"])
ai_runs_active = Gauge("relayai_ai_runs_active", "AI runs currently in progress")
tickets_active = Gauge("relayai_tickets_active", "Tickets with status != resolved/closed")
request_duration = Histogram(
    "relayai_http_request_duration_seconds",
    "HTTP request duration in seconds",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)
