"""
Synapse Glove - DSP Pipeline (Model Layer)
===========================================
Implements a 3-stage real-time Digital Signal Processing pipeline using SciPy.
Preserves internal filter states across streaming sample batches to guarantee
zero boundary discontinuities.

Pipeline Stages:
1. High-Pass Filter (Butterworth 2nd-order SOS, fc ~ 0.5 Hz):
   Eliminates baseline wander, respiratory drift, and finger pressure DC offsets.
2. Notch Filter (IIR Notch, f0 ~ 50.0 Hz, Q ~ 30):
   Surgically carves out AC mains powerline interference without harming cardiac harmonics.
3. Low-Pass Filter (Butterworth 4th-order SOS, fc ~ 40.0 Hz):
   Cuts out high-frequency muscular noise (EMG) and micro-tremor jitter.
"""

from typing import List, Tuple
import numpy as np
from scipy import signal


class DSPPipeline:
    def __init__(
        self,
        fs: float = 250.0,
        hp_cutoff: float = 0.5,
        notch_freq: float = 50.0,
        notch_q: float = 30.0,
        lp_cutoff: float = 40.0,
    ):
        self.fs = fs
        self.hp_cutoff = hp_cutoff
        self.notch_freq = notch_freq
        self.notch_q = notch_q
        self.lp_cutoff = lp_cutoff

        # Filter states
        self.sos_hp = None
        self.zi_hp = None

        self.b_notch = None
        self.a_notch = None
        self.zi_notch = None

        self.sos_lp = None
        self.zi_lp = None

        # Build initial filters
        self.update_filters(
            hp_cutoff=self.hp_cutoff,
            notch_freq=self.notch_freq,
            notch_q=self.notch_q,
            lp_cutoff=self.lp_cutoff,
            reset_state=True,
        )

    def update_filters(
        self,
        hp_cutoff: float = None,
        notch_freq: float = None,
        notch_q: float = None,
        lp_cutoff: float = None,
        reset_state: bool = False,
    ):
        """Recomputes filter coefficients dynamically when UI sliders are adjusted."""
        nyquist = 0.5 * self.fs

        if hp_cutoff is not None:
            # Bound cutoff within valid numerical limits (0.05 Hz to Nyquist - 1)
            self.hp_cutoff = max(0.05, min(hp_cutoff, nyquist - 5.0))
        if notch_freq is not None:
            self.notch_freq = max(1.0, min(notch_freq, nyquist - 1.0))
        if notch_q is not None:
            self.notch_q = max(1.0, min(notch_q, 100.0))
        if lp_cutoff is not None:
            self.lp_cutoff = max(1.0, min(lp_cutoff, nyquist - 1.0))

        # 1. High-Pass Filter (2nd order Butterworth, Second-Order Sections for numerical stability)
        hp_norm = self.hp_cutoff / nyquist
        self.sos_hp = signal.butter(2, hp_norm, btype="highpass", output="sos")
        if reset_state or self.zi_hp is None:
            self.zi_hp = signal.sosfilt_zi(self.sos_hp)

        # 2. Notch Filter (IIR Notch)
        self.b_notch, self.a_notch = signal.iirnotch(self.notch_freq, self.notch_q, fs=self.fs)
        if reset_state or self.zi_notch is None:
            self.zi_notch = signal.lfilter_zi(self.b_notch, self.a_notch)

        # 3. Low-Pass Filter (4th order Butterworth SOS)
        lp_norm = self.lp_cutoff / nyquist
        self.sos_lp = signal.butter(4, lp_norm, btype="lowpass", output="sos")
        if reset_state or self.zi_lp is None:
            self.zi_lp = signal.sosfilt_zi(self.sos_lp)

    def process_batch(self, raw_samples: List[float]) -> Tuple[List[float], List[float]]:
        """
        Processes a continuous batch of raw analog samples through all 3 stages.
        Returns:
            (filtered_samples, raw_samples)
        """
        if not raw_samples:
            return [], []

        data = np.asarray(raw_samples, dtype=np.float64)

        # Stage 1: High-Pass Filter
        data_hp, self.zi_hp = signal.sosfilt(self.sos_hp, data, zi=self.zi_hp)

        # Stage 2: 50 Hz Notch Filter
        data_notch, self.zi_notch = signal.lfilter(self.b_notch, self.a_notch, data_hp, zi=self.zi_notch)

        # Stage 3: Low-Pass Filter
        data_lp, self.zi_lp = signal.sosfilt(self.sos_lp, data_notch, zi=self.zi_lp)

        return data_lp.tolist(), data.tolist()

    def get_config(self) -> dict:
        """Returns current DSP parameters for UI synchronization."""
        return {
            "fs": self.fs,
            "hp_cutoff": self.hp_cutoff,
            "notch_freq": self.notch_freq,
            "notch_q": self.notch_q,
            "lp_cutoff": self.lp_cutoff,
        }
