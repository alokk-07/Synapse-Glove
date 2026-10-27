/**
 * Synapse Glove - UI Controls & Telemetry Handler (View Layer)
 * ============================================================
 * Manages slider interactions, Neumorphic feedback, and telemetry updates.
 */

class UIControls {
  constructor(onFilterChange, onModeChange) {
    this.onFilterChange = onFilterChange;
    this.onModeChange = onModeChange;

    // Elements
    this.sliderHp = document.getElementById('sliderHp');
    this.sliderNotch = document.getElementById('sliderNotch');
    this.sliderLp = document.getElementById('sliderLp');

    this.valHp = document.getElementById('valHp');
    this.valNotch = document.getElementById('valNotch');
    this.valLp = document.getElementById('valLp');

    this.btnResetFilters = document.getElementById('btnResetFilters');
    this.btnHardware = document.getElementById('btnHardware');
    this.btnSimulation = document.getElementById('btnSimulation');

    this.metricBpm = document.getElementById('metricBpm');
    this.metricFs = document.getElementById('metricFs');
    this.metricSnr = document.getElementById('metricSnr');
    this.metricVbat = document.getElementById('metricVbat');
    this.sqiValueText = document.getElementById('sqiValueText');
    this.sqiFillBar = document.getElementById('sqiFillBar');

    this.connectionBadge = document.getElementById('connectionBadge');
    this.connectionStatusText = document.getElementById('connectionStatusText');
    this.pulseDot = document.getElementById('pulseDot');

    this.toggleRawSignal = document.getElementById('toggleRawSignal');
    this.rawLegendItem = document.getElementById('rawLegendItem');

    this.debounceTimer = null;
    this.initEventListeners();
  }

  initEventListeners() {
    // Slider Listeners with live readout updates
    const handleSliderInput = () => {
      const hp = parseFloat(this.sliderHp.value);
      const notch = parseFloat(this.sliderNotch.value);
      const lp = parseFloat(this.sliderLp.value);

      this.valHp.textContent = `${hp.toFixed(2)} Hz`;
      this.valNotch.textContent = `${notch.toFixed(1)} Hz`;
      this.valLp.textContent = `${lp.toFixed(1)} Hz`;

      // Debounce WebSocket transmission to prevent saturation
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        if (this.onFilterChange) {
          this.onFilterChange(hp, notch, lp);
        }
      }, 50);
    };

    this.sliderHp.addEventListener('input', handleSliderInput);
    this.sliderNotch.addEventListener('input', handleSliderInput);
    this.sliderLp.addEventListener('input', handleSliderInput);

    // Reset Defaults
    this.btnResetFilters.addEventListener('click', () => {
      this.sliderHp.value = 0.50;
      this.sliderNotch.value = 50.0;
      this.sliderLp.value = 40.0;
      handleSliderInput();
    });

    // Source Toggle (Hardware vs Simulation)
    this.btnHardware.addEventListener('click', () => {
      this.btnHardware.classList.add('active');
      this.btnSimulation.classList.remove('active');
      if (this.onModeChange) this.onModeChange(false);
    });

    this.btnSimulation.addEventListener('click', () => {
      this.btnSimulation.classList.add('active');
      this.btnHardware.classList.remove('active');
      if (this.onModeChange) this.onModeChange(true);
    });

    // Raw Signal Overlay Toggle
    this.toggleRawSignal.addEventListener('change', (e) => {
      this.rawLegendItem.style.display = e.target.checked ? 'flex' : 'none';
    });
  }

  updateTelemetry(data) {
    if (data.bpm !== undefined && data.bpm !== null) {
      this.metricBpm.textContent = data.bpm;
      // Pulse dot heartbeat animation
      this.triggerHeartbeatAnimation();
    } else {
      this.metricBpm.textContent = '--';
    }

    if (data.fs_actual !== undefined) {
      this.metricFs.textContent = data.fs_actual.toFixed(1);
    }

    if (data.snr_db !== undefined) {
      this.metricSnr.textContent = data.snr_db.toFixed(1);
    }

    if (data.vbat !== undefined) {
      this.metricVbat.textContent = data.vbat.toFixed(1);
    }

    if (data.sqi !== undefined) {
      const sqi = Math.round(data.sqi);
      this.sqiValueText.textContent = `${sqi}%`;
      this.sqiFillBar.style.width = `${sqi}%`;
      
      // Color tint SQI bar based on quality
      if (sqi >= 70) {
        this.sqiFillBar.style.background = 'linear-gradient(90deg, #10b981, #059669)';
      } else if (sqi >= 40) {
        this.sqiFillBar.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
      } else {
        this.sqiFillBar.style.background = 'linear-gradient(90deg, #ef4444, #b91c1c)';
      }
    }
  }

  setConnectionState(status, message) {
    const dot = this.connectionBadge.querySelector('.status-dot');
    this.connectionStatusText.textContent = message;

    if (status === 'connected') {
      dot.className = 'status-dot connected';
    } else if (status === 'connecting') {
      dot.className = 'status-dot';
      dot.style.backgroundColor = '#f59e0b';
    } else {
      dot.className = 'status-dot';
      dot.style.backgroundColor = '#ef4444';
    }
  }

  setSourceMode(isHardwareConnected, isSimulationActive) {
    if (isHardwareConnected && !isSimulationActive) {
      this.btnHardware.classList.add('active');
      this.btnSimulation.classList.remove('active');
    } else {
      this.btnSimulation.classList.add('active');
      this.btnHardware.classList.remove('active');
    }
  }

  triggerHeartbeatAnimation() {
    this.pulseDot.classList.add('beat');
    setTimeout(() => {
      this.pulseDot.classList.remove('beat');
    }, 120);
  }
}
