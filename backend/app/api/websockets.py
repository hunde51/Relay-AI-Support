from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.ws_manager import manager
from app.services.widget_session import verify_session

router = APIRouter(tags=["websockets"])


@router.websocket("/ws/tickets")
async def ws_tickets(ws: WebSocket):
    await manager.connect_tickets(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_tickets(ws)


@router.websocket("/ws/ai-stream/{ticket_id}")
async def ws_ai_stream(ws: WebSocket, ticket_id: str):
    await manager.connect_ai(ws, ticket_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_ai(ws, ticket_id)


@router.websocket("/ws/ai-runs/{ticket_id}")
async def ws_ai_runs(ws: WebSocket, ticket_id: str):
    await manager.connect_ai(ws, ticket_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_ai(ws, ticket_id)


@router.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    await manager.connect_notifications(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_notifications(ws)


@router.websocket("/ws/widget/{ticket_id}")
async def ws_widget(ws: WebSocket, ticket_id: str, session: str = Query(...)):
    """Widget visitor WebSocket — authenticated via session token query param."""
    session_data = verify_session(session, expected_ticket_id=ticket_id)
    if not session_data:
        await ws.close(code=4001, reason="Invalid or expired session token")
        return

    await manager.connect_widget(ws, ticket_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_widget(ws, ticket_id)
