"""
mDNS / Zeroconf Service Broadcaster for Synapse Glove Backend
============================================================
Advertises the FastAPI WebSocket backend over mDNS (Multicast DNS)
so ESP32 or client devices on the same local network can discover the laptop's
IP and port without hardcoding.
"""

import socket
import logging
from zeroconf import IPVersion, ServiceInfo, Zeroconf

logger = logging.getLogger("synapse.mdns")


def get_local_ip() -> str:
    """Determine the primary local IPv4 address connected to the network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class MDNSBroadcaster:
    def __init__(self, service_name: str = "SynapseGloveServer", port: int = 8000):
        self.service_type = "_synapse._tcp.local."
        self.service_name = f"{service_name}.{self.service_type}"
        self.port = port
        self.zeroconf: Zeroconf | None = None
        self.info: ServiceInfo | None = None

    def start(self):
        try:
            local_ip = get_local_ip()
            ip_bytes = socket.inet_aton(local_ip)
            hostname = socket.gethostname()

            properties = {
                "path": "/ws/esp32",
                "version": "1.0",
                "role": "dsp-backend",
            }

            self.info = ServiceInfo(
                type_=self.service_type,
                name=self.service_name,
                addresses=[ip_bytes],
                port=self.port,
                properties=properties,
                server=f"synapse-server.local.",
            )

            self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self.zeroconf.register_service(self.info)
            logger.info(
                f"[mDNS] Broadcast active: '{self.service_name}' on {local_ip}:{self.port} (hostname: synapse-server.local)"
            )
        except Exception as e:
            logger.error(f"[mDNS] Failed to start broadcaster: {e}")

    def stop(self):
        if self.zeroconf and self.info:
            try:
                logger.info("[mDNS] Unregistering service...")
                self.zeroconf.unregister_service(self.info)
                self.zeroconf.close()
                logger.info("[mDNS] Broadcaster stopped successfully.")
            except Exception as e:
                logger.warning(f"[mDNS] Error stopping broadcaster: {e}")
            finally:
                self.zeroconf = None
                self.info = None
