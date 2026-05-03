import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect  # type: ignore[reportMissingImports]

from .eventbus import bus
from .security import websocket_require_api_key
from .service import service

logger = logging.getLogger(__name__)


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()


@router.websocket("/ws/cognitive")
async def ws_cognitive(websocket: WebSocket) -> Any:
    """WebSocket endpoint for real-time cognitive processing events."""
    # Enforce API key if configured
    websocket_require_api_key(websocket)
    await websocket.accept()
    loop = asyncio.get_running_loop()

    # Subscribe to cognitive events (zone, symbolic, glyph)
    cognitive_queue = bus.subscribe(loop, maxsize=100, policy="latest", topic="cognitive")
    symbolic_queue = bus.subscribe(loop, maxsize=100, policy="latest", topic="symbolic")
    glyph_queue = bus.subscribe(loop, maxsize=100, policy="latest", topic="glyph")

    try:
        # Send initial cognitive state
        from .services.memory_zones import get_memory_manager
        memory_manager = get_memory_manager()
        zone_metrics = memory_manager.get_zone_metrics() if hasattr(memory_manager, 'get_zone_metrics') else {}

        initial_state = {
            "type": "cognitive.state",
            "data": {
                "zone_metrics": zone_metrics,
                "active_lens": "neurotypical",  # Default
                "timestamp": __import__("time").time(),
            }
        }
        await websocket.send_text(json.dumps(initial_state))

        # Listen for events from all cognitive topics
        while True:
            # Wait for any cognitive event
            import asyncio
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(cognitive_queue.get()),
                    asyncio.create_task(symbolic_queue.get()),
                    asyncio.create_task(glyph_queue.get()),
                ],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Process the completed event
            for task in done:
                try:
                    event = task.result()
                    await websocket.send_text(json.dumps(event))
                except Exception as e:
                    logger.warning(f"Error processing cognitive event: {e}")

    except WebSocketDisconnect:
        pass
    finally:
        for q in (cognitive_queue, symbolic_queue, glyph_queue):
            try:
                bus.unsubscribe(q)
            except Exception:
                pass


@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics streaming."""
    await manager.connect(websocket)
    try:
        from .service import service

        while True:
            # Send metrics every 2 seconds
            try:
                metrics = service.metrics()
                status = service.status()

                await websocket.send_json(
                    {
                        "type": "metrics_update",
                        "data": {
                            "metrics": metrics,
                            "status": status,
                            "timestamp": __import__("time").time(),
                        },
                    }
                )
            except Exception as e:
                print(f"Error sending metrics: {e}")

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await manager.connect(websocket)
    try:
        from .service import service

        last_event_count = 0

        while True:
            try:
                # Get recent events
                events = service.recent_events(20)
                current_count = len(events)

                # Only send if new events appeared
                if current_count > last_event_count:
                    new_events = events[last_event_count:]
                    await websocket.send_json(
                        {
                            "type": "new_events",
                            "data": new_events,
                            "timestamp": __import__("time").time(),
                        }
                    )
                    last_event_count = current_count

            except Exception as e:
                print(f"Error sending events: {e}")

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/sync")
async def ws_sync(websocket: WebSocket) -> Any:
    """Catch-all WebSocket: forwards every published event on the bus to
    the connected client as a text JSON frame.

    Used by the dashboard's "live tail" view and by the integration test
    suite. Honors the same API-key gating as the cognitive endpoint.
    """
    websocket_require_api_key(websocket)
    await websocket.accept()
    loop = asyncio.get_running_loop()

    # Subscribe to ALL events on the bus (no topic filter)
    queue = bus.subscribe(loop, maxsize=200, policy="latest")

    try:
        while True:
            payload = await queue.get()
            try:
                msg = json.dumps(payload, default=str)
            except (TypeError, ValueError):
                msg = json.dumps({"type": "raw", "data": str(payload)})
            await websocket.send_text(msg)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            bus.unsubscribe(queue)
        except Exception:
            pass
