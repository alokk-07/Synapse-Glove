"""
Synapse Glove - API & WebSocket Routes (Controller Layer)
=========================================================
Registers REST endpoints and WebSocket communication channels for:
- Browser UI Dashboard (/ws/stream)
- ESP32 Hardware Node (/ws/esp32)
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.controllers.stream_controller import StreamController

logger = logging.getLogger("SynapseGlove")
router = APIRouter()


class FilterSettingsRequest(BaseModel):
    hp_cutoff: float = Field(0.5, ge=0.05, le=20.0, description="High-Pass Cutoff in Hz")
    notch_freq: float = Field(50.0, ge=10.0, le=100.0, description="Notch Filter Frequency in Hz")
    lp_cutoff: float = Field(40.0, ge=5.0, le=100.0, description="Low-Pass Cutoff in Hz")


class ModeRequest(BaseModel):
    force_simulation: bool


def register_routes(app, controller: StreamController):
    """Binds controller instance to endpoints."""

    # -------------------------------------------------------------------------
    # REST API ENDPOINTS
    # -------------------------------------------------------------------------
    @app.get("/api/status")
    async def get_status():
        return {
            "status": "operational",
            "hardware_connected": controller.is_hardware_connected,
            "simulation_active": controller.should_use_simulation(),
            "active_dashboards": len(controller.active_ui_clients),
            "filter_config": controller.dsp.get_config(),
        }

    @app.post("/api/filter-settings")
    async def update_filters(settings: FilterSettingsRequest):
        controller.update_filter_parameters(
            hp=settings.hp_cutoff,
            notch=settings.notch_freq,
            lp=settings.lp_cutoff,
        )
        await controller._broadcast_status()
        return {"status": "updated", "config": controller.dsp.get_config()}

    @app.post("/api/mode")
    async def set_mode(mode: ModeRequest):
        controller.toggle_simulation(mode.force_simulation)
        await controller._broadcast_status()
        return {
            "status": "updated",
            "force_simulation": controller.force_simulation,
            "sim_active": controller.should_use_simulation(),
        }

    # -------------------------------------------------------------------------
    # WEBSOCKET: ESP32 Hardware Streaming Endpoint
    # -------------------------------------------------------------------------
    @app.websocket("/ws/esp32")
    async def websocket_esp32_endpoint(websocket: WebSocket):
        await controller.connect_esp32(websocket)
        try:
            while True:
                data_text = await websocket.receive_text()
                try:
                    payload = json.loads(data_text)
                    # Payload format from ESP32: {"samples": [v1, v2, v3, v4, v5], "t": 12345}
                    if "samples" in payload:
                        samples = payload["samples"]
                        # Process through DSP and broadcast
                        await controller.process_and_broadcast(samples, source_tag="esp32")
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            controller.disconnect_esp32()
            await controller._broadcast_status()
        except Exception as e:
            logger.error(f"ESP32 WebSocket Error: {e}")
            controller.disconnect_esp32()
            await controller._broadcast_status()

    # -------------------------------------------------------------------------
    # WEBSOCKET: UI Dashboard Live Telemetry Endpoint
    # -------------------------------------------------------------------------
    @app.websocket("/ws/stream")
    async def websocket_ui_endpoint(websocket: WebSocket):
        await controller.connect_ui(websocket)
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    msg = json.loads(msg_text)
                    action = msg.get("action")
                    
                    if action == "set_filters":
                        controller.update_filter_parameters(
                            hp=msg.get("hp"),
                            notch=msg.get("notch"),
                            lp=msg.get("lp"),
                        )
                        await controller._broadcast_status()
                    
                    elif action == "toggle_sim":
                        controller.toggle_simulation(msg.get("force", False))
                        await controller._broadcast_status()
                        
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            controller.disconnect_ui(websocket)
        except Exception as e:
            logger.error(f"UI WebSocket Error: {e}")
            controller.disconnect_ui(websocket)
