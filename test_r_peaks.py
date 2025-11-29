"""Test R-peaks detection to identify the issue"""
import numpy as np
import neurokit2 as nk

# Create a simple test ECG signal
duration = 10  # seconds
sampling_rate = 500
ecg = nk.ecg_simulate(duration=duration, sampling_rate=sampling_rate, heart_rate=70)

print(f"Signal length: {len(ecg)} samples")
print(f"Duration: {duration}s")
print(f"Sampling rate: {sampling_rate}Hz")

# Process with NeuroKit2
signals, info = nk.ecg_process(ecg, sampling_rate=sampling_rate)

print(f"\nSignals DataFrame shape: {signals.shape}")
print(f"Signals columns: {signals.columns.tolist()}")

# Get R-peaks
r_peaks = info['ECG_R_Peaks']
print(f"\nR-peaks type: {type(r_peaks)}")
print(f"R-peaks shape: {r_peaks.shape}")
print(f"Number of R-peaks: {len(r_peaks)}")
print(f"R-peak indices (first 10): {r_peaks[:10]}")

# Test indexing
print(f"\nCleaned signal length: {len(signals['ECG_Clean'])}")
print(f"Max R-peak index: {r_peaks.max()}")
print(f"Min R-peak index: {r_peaks.min()}")

# Get amplitudes at R-peaks
amplitudes_iloc = signals['ECG_Clean'].iloc[r_peaks].values
print(f"\nAmplitudes using iloc: {amplitudes_iloc[:5]}")

# Alternative: direct numpy indexing
cleaned_np = signals['ECG_Clean'].values
amplitudes_np = cleaned_np[r_peaks]
print(f"Amplitudes using numpy: {amplitudes_np[:5]}")

# Check if they're the same
print(f"\nAre they equal? {np.allclose(amplitudes_iloc, amplitudes_np)}")

# Create time array
time_array = np.arange(len(signals)) / sampling_rate
r_peak_times = time_array[r_peaks]
print(f"\nR-peak times (first 10): {r_peak_times[:10]}")
print(f"Expected heart rate: ~70 bpm")
print(f"Time between first two peaks: {r_peak_times[1] - r_peak_times[0]:.3f}s")
print(f"Derived HR from interval: {60 / (r_peak_times[1] - r_peak_times[0]):.1f} bpm")
