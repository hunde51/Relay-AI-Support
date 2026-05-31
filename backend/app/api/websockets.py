from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager

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


@router.websocket("/ws/notifications")
async def ws_notifications(ws: WebSocket):
    await manager.connect_notifications(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_notifications(ws)
