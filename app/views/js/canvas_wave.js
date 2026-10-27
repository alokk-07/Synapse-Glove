/**
 * Synapse Glove - Canvas Waveform Oscilloscope (View Layer)
 * =========================================================
 * 60 FPS medical-grade oscilloscope renderer for continuous
 * photoplethysmogram (PPG) waveforms.
 */

class WaveformRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');

    // Ring buffers for points
    this.maxPoints = 1200; // ~4.8 seconds at 250 Hz
    this.filteredBuffer = [];
    this.rawBuffer = [];

    // Display options
    this.showRaw = false;

    // Dynamic vertical auto-scaling
    this.minY = -100;
    this.maxY = 100;
    this.targetMinY = -100;
    this.targetMaxY = 100;

    // Handle high DPI displays
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());

    // Start render loop
    this.render = this.render.bind(this);
    requestAnimationFrame(this.render);
  }

  resizeCanvas() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.displayWidth = rect.width;
    this.displayHeight = rect.height;
  }

  pushBatch(filteredBatch, rawBatch) {
    for (let i = 0; i < filteredBatch.length; i++) {
      this.filteredBuffer.push(filteredBatch[i]);
      if (rawBatch && rawBatch[i] !== undefined) {
        this.rawBuffer.push(rawBatch[i]);
      }
    }

    // Trim ring buffers
    if (this.filteredBuffer.length > this.maxPoints) {
      this.filteredBuffer.splice(0, this.filteredBuffer.length - this.maxPoints);
    }
    if (this.rawBuffer.length > this.maxPoints) {
      this.rawBuffer.splice(0, this.rawBuffer.length - this.maxPoints);
    }

    // Adapt dynamic scaling
    if (this.filteredBuffer.length > 50) {
      let bMin = Infinity;
      let bMax = -Infinity;
      for (let j = 0; j < this.filteredBuffer.length; j++) {
        const val = this.filteredBuffer[j];
        if (val < bMin) bMin = val;
        if (val > bMax) bMax = val;
      }
      const span = Math.max(20.0, bMax - bMin);
      this.targetMinY = bMin - span * 0.15;
      this.targetMaxY = bMax + span * 0.15;
    }
  }

  clear() {
    this.filteredBuffer = [];
    this.rawBuffer = [];
  }

  setShowRaw(enabled) {
    this.showRaw = enabled;
  }

  render() {
    const ctx = this.ctx;
    const w = this.displayWidth;
    const h = this.displayHeight;

    // Clear frame
    ctx.clearRect(0, 0, w, h);

    if (this.filteredBuffer.length < 2) {
      requestAnimationFrame(this.render);
      return;
    }

    // Smooth auto-scaling interpolation
    this.minY += (this.targetMinY - this.minY) * 0.05;
    this.maxY += (this.targetMaxY - this.maxY) * 0.05;
    const yRange = (this.maxY - this.minY) || 1.0;

    const toY = (val) => {
      // Invert Y because canvas origin is top-left
      return h - ((val - this.minY) / yRange) * h;
    };

    const stepX = w / (this.maxPoints - 1);
    const startIndex = Math.max(0, this.maxPoints - this.filteredBuffer.length);

    // 1. Draw Raw Unfiltered Waveform (Optional comparison trace)
    if (this.showRaw && this.rawBuffer.length > 1) {
      // Normalize raw buffer around same visual baseline
      const rawMean = this.rawBuffer.reduce((a, b) => a + b, 0) / this.rawBuffer.length;
      ctx.beginPath();
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)'; // Muted red
      ctx.setLineDash([2, 2]);

      for (let i = 0; i < this.rawBuffer.length; i++) {
        const x = (startIndex + i) * stepX;
        // Center around zero for scale matching
        const y = toY((this.rawBuffer[i] - rawMean) * 0.4);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 2. Draw Clean Filtered Pulse Waveform (Medical Neon Green CRT Trace)
    ctx.beginPath();
    ctx.lineWidth = 2.4;
    ctx.strokeStyle = '#00ff88';
    ctx.shadowColor = 'rgba(0, 255, 136, 0.6)';
    ctx.shadowBlur = 8;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    for (let i = 0; i < this.filteredBuffer.length; i++) {
      const x = (startIndex + i) * stepX;
      const y = toY(this.filteredBuffer[i]);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // 3. Leading Pulse Sweep Head (Glowing dot at the forefront)
    if (this.filteredBuffer.length > 0) {
      const lastIdx = this.filteredBuffer.length - 1;
      const headX = (startIndex + lastIdx) * stepX;
      const headY = toY(this.filteredBuffer[lastIdx]);

      ctx.beginPath();
      ctx.arc(headX, headY, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = '#00ff88';
      ctx.shadowBlur = 12;
      ctx.fill();
    }

    // Reset shadow blur
    ctx.shadowBlur = 0;

    requestAnimationFrame(this.render);
  }
}
