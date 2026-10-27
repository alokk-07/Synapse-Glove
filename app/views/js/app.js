/**
 * Synapse Glove - Client Application Orchestrator
 * ===============================================
 * Coordinates WebSocket telemetry stream, canvas rendering, and UI controls.
 */

document.addEventListener('DOMContentLoaded', () => {
  const renderer = new WaveformRenderer('waveformCanvas');

  // Clear Canvas Button
  document.getElementById('btnClearCanvas').addEventListener('click', () => {
    renderer.clear();
  });

  // Raw Signal Toggle
  const toggleRaw = document.getElementById('toggleRawSignal');
  toggleRaw.addEventListener('change', (e) => {
    renderer.setShowRaw(e.target.checked);
  });

  let socket = null;

  // Filter change callback (sends to Python backend)
  const onFilterChange = (hp, notch, lp) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        action: 'set_filters',
        hp: hp,
        notch: notch,
        lp: lp
      }));
    }
  };

  // Mode change callback (sends to Python backend)
  const onModeChange = (forceSim) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({
        action: 'toggle_sim',
        force: forceSim
      }));
    }
  };

  const ui = new UIControls(onFilterChange, onModeChange);

  // ---------------------------------------------------------------------------
  // WebSocket Telemetry Connection with Auto-Reconnect
  // ---------------------------------------------------------------------------
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/stream`;

    ui.setConnectionState('connecting', 'CONNECTING...');
    document.getElementById('footerConnectionInfo').textContent = `Attempting connection to ${wsUrl}...`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      ui.setConnectionState('connected', 'STREAMING');
      document.getElementById('footerConnectionInfo').textContent = 'Live Bidirectional WebSocket Active (250 Hz)';
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === 'data') {
          // Push samples to 60 FPS Canvas Oscilloscope
          renderer.pushBatch(msg.filtered, msg.raw);

          // Update Health Telemetry Metrics
          ui.updateTelemetry(msg);

          // Update status badge label based on data source
          if (msg.source === 'esp32') {
            ui.setConnectionState('connected', 'ESP32 HARDWARE LIVE');
          } else {
            ui.setConnectionState('connected', 'SIMULATOR ACTIVE');
          }

        } else if (msg.type === 'init' || msg.type === 'status') {
          if (msg.config) {
            // Synchronize sliders if provided
            if (msg.config.hp_cutoff) {
              ui.sliderHp.value = msg.config.hp_cutoff;
              ui.valHp.textContent = `${msg.config.hp_cutoff.toFixed(2)} Hz`;
            }
            if (msg.config.notch_freq) {
              ui.sliderNotch.value = msg.config.notch_freq;
              ui.valNotch.textContent = `${msg.config.notch_freq.toFixed(1)} Hz`;
            }
            if (msg.config.lp_cutoff) {
              ui.sliderLp.value = msg.config.lp_cutoff;
              ui.valLp.textContent = `${msg.config.lp_cutoff.toFixed(1)} Hz`;
            }
          }
          ui.setSourceMode(msg.hardware_connected, msg.sim_active);
        }

      } catch (err) {
        console.error('Error parsing incoming telemetry frame:', err);
      }
    };

    socket.onclose = () => {
      ui.setConnectionState('disconnected', 'DISCONNECTED');
      document.getElementById('footerConnectionInfo').textContent = 'Disconnected. Retrying connection in 2s...';
      setTimeout(connectWebSocket, 2000);
    };

    socket.onerror = (err) => {
      console.error('WebSocket Error:', err);
      socket.close();
    };
  }

  // Connect immediately
  connectWebSocket();
});
