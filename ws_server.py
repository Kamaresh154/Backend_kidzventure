"""
KidzVenture WebSocket Chat Server
Run alongside the FastAPI backend: python ws_server.py
Port: 8001
"""
import asyncio
import json
import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_chat")

# In-memory message store: employee_id -> list of messages
# In production, replace with Redis or DB persistence
message_store: Dict[str, List[dict]] = defaultdict(list)

# Active connections: employee_id -> set of websockets
connections: Dict[str, Set[WebSocketServerProtocol]] = defaultdict(set)


async def broadcast_to_room(employee_id: str, message: dict, exclude: WebSocketServerProtocol = None):
    """Broadcast a message to all connections in a room."""
    dead = set()
    for ws in connections[employee_id]:
        if ws is exclude:
            continue
        try:
            await ws.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            dead.add(ws)
    for ws in dead:
        connections[employee_id].discard(ws)


async def handler(websocket: WebSocketServerProtocol, path: str):
    """
    WebSocket path: /ws/chat/{employee_id}
    Protocol:
      Client -> Server:
        { type: "auth", user: "Name", role: "super_admin|employee|admin" }
        { type: "message", message: { id, employee_id, from_name, from_role, content, sent_at } }
      Server -> Client:
        { type: "history", messages: [...] }
        { type: "message", message: {...} }
        { type: "ack", id: "..." }
    """
    # Parse employee_id from path: /ws/chat/emp_123
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "ws" or parts[1] != "chat":
        await websocket.close(1008, "Invalid path")
        return

    employee_id = parts[2]
    logger.info(f"New connection for employee {employee_id}")

    # Register connection
    connections[employee_id].add(websocket)

    try:
        # Wait for auth message
        try:
            raw = await asyncio.wait_for(websocket.recv(), timeout=10)
            auth = json.loads(raw)
            if auth.get("type") != "auth":
                await websocket.close(1008, "Expected auth message")
                return
            user_name = auth.get("user", "Unknown")
            user_role = auth.get("role", "employee")
            logger.info(f"Authenticated: {user_name} ({user_role}) in room {employee_id}")
        except asyncio.TimeoutError:
            await websocket.close(1008, "Auth timeout")
            return

        # Send message history
        history = message_store.get(employee_id, [])
        await websocket.send(json.dumps({"type": "history", "messages": history}))

        # Message loop
        async for raw in websocket:
            try:
                data = json.loads(raw)
                if data.get("type") == "message":
                    msg = data.get("message", {})
                    # Ensure required fields
                    if not msg.get("id"):
                        msg["id"] = f"msg_{datetime.utcnow().timestamp()}"
                    if not msg.get("sent_at"):
                        msg["sent_at"] = datetime.utcnow().isoformat()
                    msg["employee_id"] = employee_id

                    # Persist
                    message_store[employee_id].append(msg)
                    # Keep last 500 messages per room
                    if len(message_store[employee_id]) > 500:
                        message_store[employee_id] = message_store[employee_id][-500:]

                    # Broadcast to all in room (including sender for confirmation)
                    await broadcast_to_room(employee_id, {"type": "message", "message": msg})
                    logger.info(f"Message from {msg.get('from_name')} in room {employee_id}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from {employee_id}")
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Connection closed for employee {employee_id}")
    finally:
        connections[employee_id].discard(websocket)
        if not connections[employee_id]:
            del connections[employee_id]


async def main():
    host = "0.0.0.0"
    port = 8001
    logger.info(f"Starting WebSocket chat server on ws://{host}:{port}")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
