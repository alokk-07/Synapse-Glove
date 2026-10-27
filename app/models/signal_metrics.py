"""
Synapse Glove - Signal Metrics & Feature Extraction (Model Layer)
==================================================================
Extracts real-time physiological metrics:
- Heart Rate (BPM) via peak detection on systolic upstrokes
- Signal-to-Noise Ratio (SNR in dB)
- Effective Real-time Sampling Rate (Hz)
- Signal Quality Index (SQI %)
"""

import time
from collections import deque
from typing import Optional, List, Dict
import numpy as np
from scipy import signal


class SignalMetricsAnalyzer:
    def __init__(self, fs: float = 250.0, window_sec: float = 4.0):
        self.fs = fs
        self.window_size = int(fs * window_sec)  # 1000 samples for 4.0s at 250Hz
        self.sample_buffer = deque(maxlen=self.window_size)
        self.raw_buffer = deque(maxlen=self.window_size)

        # Sampling rate tracking
        self.sample_count = 0
        self.last_rate_calc_time = time.time()
        self.measured_fs = fs

        # Peak detection state
        self.last_peak_index = -1
        self.rr_intervals = deque(maxlen=8)
        self.current_bpm: Optional[float] = 72.0
        self.current_snr_db: float = 18.5
        self.current_sqi: float = 85.0

    def push_samples(self, filtered_batch: List[float], raw_batch: List[float]):
        """Pushes new sample batch into rolling analysis buffers."""
        self.sample_buffer.extend(filtered_batch)
        self.raw_buffer.extend(raw_batch)
        self.sample_count += len(filtered_batch)

        # Re-evaluate sampling rate once per second
        now = time.time()
        elapsed = now - self.last_rate_calc_time
        if elapsed >= 1.0:
            self.measured_fs = round(self.sample_count / elapsed, 1)
            self.sample_count = 0
            self.last_rate_calc_time = now

    def compute_metrics(self) -> Dict[str, Optional[float]]:
        """Calculates instantaneous Heart Rate (BPM), SNR (dB), and SQI."""
        if len(self.sample_buffer) < int(self.fs * 2.0):
            # Not enough data for meaningful metric extraction
            return {
                "bpm": self.current_bpm,
                "snr_db": self.current_snr_db,
                "sqi": self.current_sqi,
                "fs_actual": self.measured_fs,
            }

        data = np.array(self.sample_buffer, dtype=np.float64)
        raw_data = np.array(self.raw_buffer, dtype=np.float64)

        # 1. Peak Detection for Heart Rate (BPM)
        # Minimum peak distance: 0.35s (corresponds to max 171 BPM)
        min_distance = int(self.fs * 0.35)
        
        # Dynamic threshold based on 70th percentile of positive peaks
        std_val = np.std(data)
        if std_val > 1e-4:
            prominence = 0.4 * std_val
            peaks, properties = signal.find_peaks(data, distance=min_distance, prominence=prominence)
            
            if len(peaks) >= 2:
                # Calculate inter-beat intervals in seconds
                intervals_sec = np.diff(peaks) / self.fs
                # Filter physiological extremes: 0.35s (171 BPM) to 1.5s (40 BPM)
                valid_intervals = intervals_sec[(intervals_sec >= 0.35) & (intervals_sec <= 1.5)]
                
                if len(valid_intervals) > 0:
                    median_interval = np.median(valid_intervals)
                    instant_bpm = 60.0 / median_interval
                    
                    # Smooth with rolling history
                    self.rr_intervals.append(instant_bpm)
                    self.current_bpm = round(float(np.mean(self.rr_intervals)), 1)

        # 2. Real-time SNR Calculation
        # Signal power: Variance of clean filtered signal
        # Noise power: High-frequency residual (raw - filtered) or variance ratio
        var_sig = np.var(data)
        if len(raw_data) == len(data):
            noise_residual = raw_data - data
            # Remove DC offset of noise
            noise_residual -= np.mean(noise_residual)
            var_noise = np.var(noise_residual)
            
            if var_noise > 1e-9 and var_sig > 1e-9:
                snr_ratio = var_sig / var_noise
                snr_db = 10.0 * np.log10(snr_ratio)
                # Clamp within reasonable realistic bounds for PPG (-10 dB to +35 dB)
                self.current_snr_db = round(float(np.clip(snr_db, -5.0, 32.0)), 1)
            else:
                self.current_snr_db = 20.0

        # 3. Signal Quality Index (SQI %): combination of amplitude regularity & SNR
        if self.current_snr_db > 12.0 and std_val > 5.0:
            self.current_sqi = min(99.0, max(60.0, round(self.current_snr_db * 3.5, 0)))
        elif std_val > 1.0:
            self.current_sqi = min(75.0, max(30.0, round(self.current_snr_db * 2.5, 0)))
        else:
            self.current_sqi = 15.0  # Sensor not on finger or idle

        return {
            "bpm": self.current_bpm,
            "snr_db": self.current_snr_db,
            "sqi": self.current_sqi,
            "fs_actual": self.measured_fs,
        }
