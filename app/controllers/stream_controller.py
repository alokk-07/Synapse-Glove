"""
Synapse Glove - Stream Controller (Controller Layer)
===================================================
Manages bidirectional WebSockets between:
1. ESP32 Hardware Wearable Node (/ws/esp32)
2. Swiss Neumorphic Web Dashboard Clients (/ws/stream)

Coordinates the Model layer (DSPPipeline, SignalMetricsAnalyzer, PPGSimulator),
ensuring zero-latency signal filtering and broadcast at 50 packets/sec (250 Hz).
"""

import asyncio
import json
import logging
from typing import Set, List
from fastapi import WebSocket, WebSocketDisconnect

from app.models.dsp_pipeline import DSPPipeline
from app.models.signal_metrics import SignalMetricsAnalyzer
from app.models.signal_simulator import PPGSimulator

logger = logging.getLogger("SynapseGlove")


class StreamController:
    def __init__(self):
        self.fs = 250.0
        self.dsp = DSPPipeline(fs=self.fs, hp_cutoff=0.5, notch_freq=50.0, lp_cutoff=40.0)
        self.metrics = SignalMetricsAnalyzer(fs=self.fs)
        self.simulator = PPGSimulator(fs=self.fs, base_bpm=72.0)

        # Connection registry
        self.active_ui_clients: Set[WebSocket] = set()
        self.esp32_ws: WebSocket = None
        self.is_hardware_connected: bool = False
        self.force_simulation: bool = False

        # Background simulator task
        self.sim_task: asyncio.Task = None

    async def start(self):
        """Starts background streaming engine."""
        if self.sim_task is None or self.sim_task.done():
            self.sim_task = asyncio.create_task(self._simulation_loop())
            logger.info("Synapse Glove Stream Controller started.")

    async def stop(self):
        """Clean shutdown."""
        if self.sim_task and not self.sim_task.done():
            self.sim_task.cancel()

    # -------------------------------------------------------------------------
    # UI Web Client Connection Management
    # -------------------------------------------------------------------------
    async def connect_ui(self, websocket: WebSocket):
        await websocket.accept()
        self.active_ui_clients.add(websocket)
        logger.info(f"UI Client connected. Total active UI clients: {len(self.active_ui_clients)}")
        
        # Send initial configuration state
        init_payload = {
            "type": "init",
            "config": self.dsp.get_config(),
            "hardware_connected": self.is_hardware_connected,
            "sim_active": self.should_use_simulation(),
        }
        await websocket.send_text(json.dumps(init_payload))

    def disconnect_ui(self, websocket: WebSocket):
        self.active_ui_clients.discard(websocket)
        logger.info(f"UI Client disconnected. Remaining: {len(self.active_ui_clients)}")

    # -------------------------------------------------------------------------
    # ESP32 Hardware Connection Management
    # -------------------------------------------------------------------------
    async def connect_esp32(self, websocket: WebSocket):
        await websocket.accept()
        self.esp32_ws = websocket
        self.is_hardware_connected = True
        logger.info("⚡ ESP32 Wearable Node connected via WebSocket (/ws/esp32)!")
        await self._broadcast_status()

    def disconnect_esp32(self):
        self.esp32_ws = None
        self.is_hardware_connected = False
        logger.info("❌ ESP32 Wearable Node disconnected.")

    # -------------------------------------------------------------------------
    # Processing & Broadcast Pipeline
    # -------------------------------------------------------------------------
    def should_use_simulation(self) -> bool:
        """Use simulator if forced, or if hardware is not connected."""
        return self.force_simulation or not self.is_hardware_connected

    async def process_and_broadcast(self, raw_samples: List[float], source_tag: str):
        """Pushes raw samples through DSP and broadcasts to all UI dashboards."""
        if not raw_samples or not self.active_ui_clients:
            return

        # 1. Apply real-time 3-stage SciPy filtering
        filtered_samples, raw_list = self.dsp.process_batch(raw_samples)

        # 2. Update real-time metrics
        self.metrics.push_samples(filtered_samples, raw_list)
        metrics_data = self.metrics.compute_metrics()

        # 3. Form unified broadcast payload
        payload = {
            "type": "data",
            "source": source_tag,
            "raw": [round(v, 1) for v in raw_list],
            "filtered": [round(v, 2) for v in filtered_samples],
            "bpm": metrics_data["bpm"],
            "snr_db": metrics_data["snr_db"],
            "sqi": metrics_data["sqi"],
            "fs_actual": metrics_data["fs_actual"],
            "vbat": 3.0 if source_tag == "esp32" else 3.2,
        }

        # 4. Broadcast to all active UI web clients
        dead_clients = []
        msg_str = json.dumps(payload)
        for client in self.active_ui_clients:
            try:
                await client.send_text(msg_str)
            except Exception:
                dead_clients.append(client)

        for dead in dead_clients:
            self.active_ui_clients.discard(dead)

    # -------------------------------------------------------------------------
    # Simulation Loop (Runs when ESP32 is offline or simulation is forced)
    # -------------------------------------------------------------------------
    async def _simulation_loop(self):
        """Emits batches of 5 samples every 20ms (exactly 250 Hz)."""
        interval = 0.020  # 20 milliseconds
        while True:
            try:
                await asyncio.sleep(interval)
                if self.should_use_simulation() and self.active_ui_clients:
                    sim_samples = self.simulator.generate_chunk(n_samples=5)
                    await self.process_and_broadcast(sim_samples, source_tag="simulation")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")

    # -------------------------------------------------------------------------
    # Dynamic Parameter Updates (Sliders & Toggles)
    # -------------------------------------------------------------------------
    def update_filter_parameters(self, hp: float = None, notch: float = None, lp: float = None):
        """Dynamically reconfigures DSP filter cutoffs."""
        self.dsp.update_filters(hp_cutoff=hp, notch_freq=notch, lp_cutoff=lp)
        logger.info(f"DSP Filters Updated: HP={self.dsp.hp_cutoff}Hz, Notch={self.dsp.notch_freq}Hz, LP={self.dsp.lp_cutoff}Hz")

    def toggle_simulation(self, force: bool):
        self.force_simulation = force
        logger.info(f"Simulation override set to: {self.force_simulation}")

    async def _broadcast_status(self):
        payload = json.dumps({
            "type": "status",
            "hardware_connected": self.is_hardware_connected,
            "sim_active": self.should_use_simulation(),
            "config": self.dsp.get_config(),
        })
        for client in list(self.active_ui_clients):
            try:
                await client.send_text(payload)
            except Exception:
                pass
