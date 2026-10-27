"""
Synapse Glove - Synthetic PPG Signal Generator (Model Layer)
=============================================================
Generates a realistic biological Photoplethysmogram (PPG) waveform
complete with:
- Morphologically accurate systolic peak and dicrotic notch
- Low-frequency baseline wander (mimicking respiration & contact pressure drift)
- 50 Hz electromagnetic powerline interference
- High-frequency muscular tremor noise (EMG)

Used for instant end-to-end verification of the DSP pipeline and UI.
"""

import math
from typing import List
import numpy as np


class PPGSimulator:
    def __init__(self, fs: float = 250.0, base_bpm: float = 72.0):
        self.fs = fs
        self.base_bpm = base_bpm
        self.time_step = 1.0 / fs
        self.current_time = 0.0

        # Noise amplitude parameters
        self.baseline_wander_amp = 180.0   # Large slow drift (~0.25 Hz)
        self.powerline_hum_amp = 65.0      # 50 Hz mains hum
        self.tremor_noise_amp = 25.0       # High-frequency jitter
        self.pulse_amplitude = 600.0       # Cardiac pulsatile amplitude
        self.dc_baseline = 2048.0          # ADC midpoint (12-bit ~2048)

    def _single_pulse_wave(self, phase: float) -> float:
        """
        Synthesizes a realistic arterial PPG pulse profile over phase [0, 1).
        Contains a steep systolic upstroke, systolic peak, and a secondary dicrotic peak.
        """
        # Systolic peak: asymmetric Gaussian centered around phase = 0.2
        p1 = math.exp(-((phase - 0.20) ** 2) / (2 * (0.07 ** 2)))
        
        # Dicrotic notch and diastolic peak: centered around phase = 0.42
        p2 = 0.45 * math.exp(-((phase - 0.42) ** 2) / (2 * (0.09 ** 2)))

        return p1 + p2

    def generate_chunk(self, n_samples: int = 5) -> List[float]:
        """Generates n_samples of noisy biological raw sensor data."""
        raw_samples = []
        cardiac_freq = self.base_bpm / 60.0  # e.g., 72 / 60 = 1.2 Hz
        period = 1.0 / cardiac_freq

        for _ in range(n_samples):
            t = self.current_time

            # 1. Cardiac Pulse Component
            phase = (t % period) / period
            cardiac_val = self.pulse_amplitude * self._single_pulse_wave(phase)

            # 2. Baseline Wander (Respiration ~0.25 Hz + slow postural sway ~0.08 Hz)
            wander = (
                self.baseline_wander_amp * math.sin(2 * math.pi * 0.25 * t)
                + (self.baseline_wander_amp * 0.5) * math.sin(2 * math.pi * 0.08 * t + 1.2)
            )

            # 3. 50 Hz Powerline Hum
            mains_hum = self.powerline_hum_amp * math.sin(2 * math.pi * 50.0 * t)

            # 4. High-frequency Muscular Tremor & Thermal Noise (Random normal)
            tremor = np.random.normal(0, self.tremor_noise_amp)

            # Composite raw analog ADC reading
            total_raw = self.dc_baseline + cardiac_val + wander + mains_hum + tremor

            # Bound to 12-bit ADC range (0 - 4095)
            clamped_val = max(0.0, min(4095.0, total_raw))
            raw_samples.append(clamped_val)

            self.current_time += self.time_step

        return raw_samples
