"""
Synapse Glove - Main FastAPI Application (Entrypoint)
=====================================================
Starts the biomedical telemetry server, mounts the Neumorphic UI,
and registers WebSocket and REST interfaces.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.controllers.stream_controller import StreamController
from app.controllers.routes import register_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

controller = StreamController()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch DSP streaming engine & simulation background loop
    await controller.start()
    yield
    # Shutdown: Cleanly terminate background tasks
    await controller.stop()


app = FastAPI(
    title="Synapse Glove Telemetry & DSP Backend",
    description="Real-Time Biomedical Pulse Wave Telemetry & Digital Signal Processing",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local cross-origin connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Controller Endpoints & WebSockets
register_routes(app, controller)

# Mount Views (Static Files)
views_dir = Path(__file__).parent / "views"
app.mount("/static", StaticFiles(directory=views_dir), name="static")


@app.get("/")
async def serve_index():
    """Serves the Swiss Minimalist Neumorphic Dashboard."""
    return FileResponse(views_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 so ESP32 on the local Wi-Fi network can connect directly to this machine's IP
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
