from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        self._ticket_clients: list[WebSocket] = []
        self._ai_clients: dict[str, list[WebSocket]] = {}  # ticket_id → clients
        self._notification_clients: list[WebSocket] = []

    async def connect_tickets(self, ws: WebSocket):
        await ws.accept()
        self._ticket_clients.append(ws)

    def disconnect_tickets(self, ws: WebSocket):
        self._ticket_clients.remove(ws)

    async def connect_ai(self, ws: WebSocket, ticket_id: str):
        await ws.accept()
        self._ai_clients.setdefault(ticket_id, []).append(ws)

    def disconnect_ai(self, ws: WebSocket, ticket_id: str):
        if ticket_id in self._ai_clients:
            self._ai_clients[ticket_id].remove(ws)

    async def connect_notifications(self, ws: WebSocket):
        await ws.accept()
        self._notification_clients.append(ws)

    def disconnect_notifications(self, ws: WebSocket):
        if ws in self._notification_clients:
            self._notification_clients.remove(ws)

    async def broadcast_ticket(self, data: dict):
        for ws in list(self._ticket_clients):
            await ws.send_text(json.dumps(data))

    async def broadcast_notification(self, data: dict):
        for ws in list(self._notification_clients):
            await ws.send_text(json.dumps(data))

    async def stream_ai_step(self, ticket_id: str, step: dict):
        for ws in list(self._ai_clients.get(ticket_id, [])):
            await ws.send_text(json.dumps(step))

    async def stream_tool_call(self, ticket_id: str, call: dict):
        """Stream tool call events to AI clients for a ticket."""
        for ws in list(self._ai_clients.get(ticket_id, [])):
            await ws.send_text(json.dumps({"tool_call": call}))


manager = ConnectionManager()
