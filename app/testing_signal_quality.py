#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Signal Quality Functions

This script tests all functions in signal_quality.py individually and visualizes
their inputs and outputs using Device ECG data. Tests the ambulatory ECG quality
assessment system with baseline wander detection for motion artifact classification.

Classification System:
- REJECTED: kSQI < 3.0 (external artifacts/motion) 
- UNRELIABLE: mSQI < 0.5 (poor morphological quality)
- GOOD: kSQI > 5.0 AND mSQI > 0.8 (optimal quality)
- ACCEPTABLE: mSQI > 0.8 AND kSQI < 4.0 (baseline wander/stepping artifact)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import neurokit2 as nk
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from signal_quality import (
    assess_ecg_quality,
    analyze_sliding_windows,
    calculate_window_metrics,
    get_module_info
)

def load_device_data(filepath: str, channels: list = ['CH2', 'CH3', 'CH4'], duration: float = None):
    """Load and parse Device_1_Volts.txt data"""
    print(f"=== LOADING DEVICE DATA ===")
    print(f"File: {filepath}")
    print(f"Channels: {channels}")
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Parse metadata
    metadata = {}
    data_start_idx = 0
    
    for i, line in enumerate(lines):
        if 'Record #:' in line:
            metadata['record_number'] = line.split(':')[1].strip()
        elif 'Notes' in line and ':' in line:
            metadata['notes'] = lines[i + 1].strip() if i + 1 < len(lines) else ''
        elif 'Gain' in line:
            metadata['gain'] = line.strip()
        elif line.strip().startswith('CH1'):
            data_start_idx = i + 1
            break
    
    print(f"Metadata found: {metadata}")
    
    # Parse data
    data_lines = lines[data_start_idx:]
    data_rows = []
    for line in data_lines:
        line = line.strip()
        if line:
            values = [float(x) for x in line.split('\t')]
            data_rows.append(values)
    
    # Create DataFrame
    df = pd.DataFrame(
        data_rows,
        columns=['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7', 'CH8']
    )
    df = df * 1000  # Convert to millivolts
    sampling_rate = 500
    df['time'] = np.arange(len(df)) / sampling_rate
    
    # Apply duration limit if specified
    if duration is not None:
        max_samples = int(duration * sampling_rate)
        df = df.iloc[:max_samples]
    
    print(f"Loaded {len(df)} samples ({len(df)/sampling_rate:.1f}s) at {sampling_rate} Hz")
    print(f"Available channels: {[col for col in df.columns if col.startswith('CH')]}")
    
    return df, metadata, sampling_rate

def process_channel_data(df: pd.DataFrame, channel: str, sampling_rate: int):
    """Process raw channel data and return cleaned ECG signal"""
    print(f"\n=== PROCESSING CHANNEL {channel} ===")
    
    if channel not in df.columns:
        raise ValueError(f"Channel {channel} not found in data")
    
    raw_signal = df[channel].values
    print(f"Raw signal: {len(raw_signal)} samples, range: {np.min(raw_signal):.2f} to {np.max(raw_signal):.2f} mV")
    
    # Check for constant signal
    if np.std(raw_signal) < 0.01:  # Very low variability
        print(f"WARNING: Channel {channel} appears to be constant or have very low variability")
        print(f"Standard deviation: {np.std(raw_signal):.4f}")
        raise ValueError(f"Channel {channel} has constant/invalid signal")
    
    # Process with NeuroKit2
    try:
        signals, info = nk.ecg_process(raw_signal, sampling_rate=sampling_rate)
        cleaned_signal = signals['ECG_Clean'].values
        r_peaks = info['ECG_R_Peaks']
        
        print(f"Cleaned signal: {len(cleaned_signal)} samples")
        print(f"R-peaks detected: {len(r_peaks)}")
        
        if len(r_peaks) > 1:
            print(f"Mean HR: {signals['ECG_Rate'].mean():.1f} BPM")
        else:
            print("WARNING: Insufficient R-peaks for HR calculation")
        
        return raw_signal, cleaned_signal, r_peaks, signals, info
        
    except Exception as e:
        print(f"ERROR in ECG processing: {e}")
        raise

def test_assess_ecg_quality(cleaned_signal: np.ndarray, sampling_rate: int, channel: str):
    """Test the main assess_ecg_quality function"""
    print(f"\n" + "="*60)
    print(f"TESTING: assess_ecg_quality() - Channel {channel}")
    print(f"="*60)
    
    result = assess_ecg_quality(cleaned_signal, sampling_rate)
    
    print(f"\nRESULT STRUCTURE:")
    for key, value in result.items():
        if isinstance(value, pd.DataFrame):
            print(f"  {key}: DataFrame with {len(value)} rows, {len(value.columns)} columns")
            print(f"    Columns: {list(value.columns)}")
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], list):
            print(f"  {key}: List of {len(value)} segment pairs")
        elif isinstance(value, dict):
            print(f"  {key}: Dict with keys: {list(value.keys())}")
        else:
            print(f"  {key}: {type(value).__name__} = {value}")
    
    return result

def test_analyze_sliding_windows(cleaned_signal: np.ndarray, r_peaks: np.ndarray, 
                                sampling_rate: int, channel: str):
    """Test the analyze_sliding_windows function"""
    print(f"\n" + "="*60)
    print(f"TESTING: analyze_sliding_windows() - Channel {channel}")
    print(f"="*60)
    
    window_size = 10 * sampling_rate  # 10 seconds
    stride = 1 * sampling_rate        # 1 second
    max_start = len(cleaned_signal) - window_size
    
    print(f"Parameters:")
    print(f"  Window size: {window_size} samples (10s)")
    print(f"  Stride: {stride} samples (1s)")
    print(f"  Max start: {max_start}")
    print(f"  Expected windows: {(max_start // stride) + 1}")
    
    if max_start <= 0:
        print("ERROR: Signal too short for sliding windows")
        return None
    
    result = analyze_sliding_windows(cleaned_signal, r_peaks, sampling_rate, 
                                   window_size, stride, max_start)
    
    print(f"\nRESULT:")
    for key, value in result.items():
        if isinstance(value, pd.DataFrame):
            print(f"  {key}: DataFrame with {len(value)} rows")
        else:
            print(f"  {key}: {value}")
    
    return result

def test_calculate_window_metrics(cleaned_signal: np.ndarray, r_peaks: np.ndarray,
                                 sampling_rate: int, channel: str):
    """Test the calculate_window_metrics function on multiple windows"""
    print(f"\n" + "="*60)
    print(f"TESTING: calculate_window_metrics() - Channel {channel}")
    print(f"="*60)
    
    window_size = 10 * sampling_rate
    metrics_list = []
    
    # Test first 3 windows
    for i in range(3):
        start_idx = i * sampling_rate  # 1-second stride
        end_idx = start_idx + window_size
        
        if end_idx > len(cleaned_signal):
            break
            
        print(f"\nTesting Window {i+1}: samples {start_idx}-{end_idx} ({start_idx/sampling_rate:.1f}s-{end_idx/sampling_rate:.1f}s)")
        
        segment = cleaned_signal[start_idx:end_idx]
        window_peaks = r_peaks[(r_peaks >= start_idx) & (r_peaks < end_idx)]
        relative_peaks = window_peaks - start_idx
        
        print(f"  Segment length: {len(segment)} samples")
        print(f"  Peaks in window: {len(window_peaks)}")
        print(f"  Relative peaks: {relative_peaks}")
        
        try:
            metrics = calculate_window_metrics(segment, relative_peaks, sampling_rate, 
                                             start_idx, end_idx, i+1)
            metrics_list.append(metrics)
            
            print(f"  METRICS:")
            for key, value in metrics.items():
                print(f"    {key}: {value}")
                
        except Exception as e:
            print(f"  ERROR: {e}")
    
    return metrics_list

def test_module_info():
    """Test the module info function"""
    print(f"\n" + "="*60)
    print(f"TESTING: get_module_info()")
    print(f"="*60)
    
    info = get_module_info()
    print("\nModule Information:")
    for key, value in info.items():
        if isinstance(value, list):
            print(f"  {key}:")
            for item in value:
                print(f"    - {item}")
        elif isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subval in value.items():
                print(f"    {subkey}: {subval}")
        else:
            print(f"  {key}: {value}")
    
    return info

def visualize_results(df: pd.DataFrame, channels: list, results: dict):
    """Create comprehensive visualizations of all results"""
    print(f"\n" + "="*60)
    print(f"CREATING VISUALIZATIONS")
    print(f"="*60)
    
    fig, axes = plt.subplots(len(channels), 3, figsize=(20, 6*len(channels)))
    
    for i, channel in enumerate(channels):
        channel_results = results[channel]
        raw_signal = channel_results['raw_signal']
        cleaned_signal = channel_results['cleaned_signal']
        r_peaks = channel_results['r_peaks']
        assess_result = channel_results['assess_result']
        sampling_rate = 500
        
        time_array = np.arange(len(raw_signal)) / sampling_rate
        
        # Plot 1: Raw vs Cleaned Signal
        ax1 = axes[i, 0] if len(channels) > 1 else axes[0]
        ax1.plot(time_array, raw_signal, alpha=0.7, label='Raw Signal', color='gray')
        ax1.plot(time_array, cleaned_signal, label='Cleaned Signal', color='blue')
        ax1.scatter(time_array[r_peaks], cleaned_signal[r_peaks], color='red', s=30, alpha=0.8, label='R-peaks')
        ax1.set_title(f'{channel}: Raw vs Cleaned Signal')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Amplitude (mV)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Quality Analysis Windows
        ax2 = axes[i, 1] if len(channels) > 1 else axes[1]
        ax2.plot(time_array, cleaned_signal, color='lightblue', alpha=0.7, label='ECG Signal')
        
        if assess_result and 'results_df' in assess_result and not assess_result['results_df'].empty:
            results_df = assess_result['results_df']
            
            for _, row in results_df.iterrows():
                start_time = row['start_time']
                end_time = row['end_time']
                status = row['status']
                
                color_map = {'GOOD': 'green', 'UNRELIABLE': 'orange', 'REJECTED': 'red'}
                color = color_map.get(status, 'gray')
                
                ax2.axvspan(start_time, end_time, alpha=0.3, color=color, 
                           label=status if status not in [l.get_text() for l in ax2.get_legend_handles_labels()[1]] else "")
        
        # Highlight best segment
        if assess_result and 'best_segment_indices' in assess_result:
            best_start, best_end = assess_result['best_segment_indices']
            best_start_time = best_start / sampling_rate
            best_end_time = best_end / sampling_rate
            ax2.axvspan(best_start_time, best_end_time, alpha=0.5, color='gold', 
                       linestyle='--', linewidth=2, label='Best Segment')
        
        ax2.set_title(f'{channel}: Quality Assessment Windows')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Amplitude (mV)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Quality Metrics Over Time
        ax3 = axes[i, 2] if len(channels) > 1 else axes[2]
        
        if assess_result and 'results_df' in assess_result and not assess_result['results_df'].empty:
            results_df = assess_result['results_df']
            
            # Plot quality scores
            window_times = (results_df['start_time'] + results_df['end_time']) / 2
            ax3.scatter(window_times, results_df['mSQI'], c=results_df['kSQI'], 
                       s=60, alpha=0.8, cmap='viridis', label='mSQI vs kSQI')
            
            # Add colorbar
            scatter = ax3.scatter(window_times, results_df['mSQI'], c=results_df['kSQI'], 
                                s=60, alpha=0.8, cmap='viridis')
            plt.colorbar(scatter, ax=ax3, label='kSQI (Kurtosis)')
            
            # Add threshold lines
            ax3.axhline(y=0.8, color='green', linestyle='--', alpha=0.7, label='mSQI Good Threshold (0.8)')
            ax3.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='mSQI Unreliable Threshold (0.5)')
        
        ax3.set_title(f'{channel}: Quality Metrics (mSQI vs Time, colored by kSQI)')
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('mSQI (Morphological Quality)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.savefig('signal_quality_analysis.png', dpi=300, bbox_inches='tight')
    print("Visualization saved as 'signal_quality_analysis.png'")
    plt.show()

def test_functions_with_io_documentation(cleaned_signal: np.ndarray, r_peaks: np.ndarray, 
                                        sampling_rate: int, channel: str):
    """Test all signal quality functions with detailed input/output documentation"""
    
    # FUNCTION 1: assess_ecg_quality
    print("\n" + "="*80)
    print("FUNCTION 1: assess_ecg_quality()")
    print("="*80)
    print("PURPOSE: Main ambulatory ECG quality assessment with sliding window analysis")
    print("\nINPUTS:")
    print(f"  ecg_cleaned: numpy.ndarray shape {cleaned_signal.shape}, dtype {cleaned_signal.dtype}")
    print(f"    - Range: {np.min(cleaned_signal):.3f} to {np.max(cleaned_signal):.3f}")
    print(f"    - Mean: {np.mean(cleaned_signal):.3f}, Std: {np.std(cleaned_signal):.3f}")
    print(f"  sampling_rate: int = {sampling_rate}")
    
    print("\nEXECUTING...")
    assess_result = assess_ecg_quality(cleaned_signal, sampling_rate)
    
    print("\nOUTPUTS:")
    print(f"  Return type: {type(assess_result)}")
    for key, value in assess_result.items():
        if isinstance(value, pd.DataFrame):
            print(f"  {key}: pandas.DataFrame")
            print(f"    - Shape: {value.shape}")
            print(f"    - Columns: {list(value.columns)}")
            if not value.empty:
                print(f"    - Sample row 0: {dict(value.iloc[0])}")
        elif isinstance(value, list):
            print(f"  {key}: list with {len(value)} elements")
            if value and isinstance(value[0], list):
                print(f"    - Element 0: {value[0]}")
        elif isinstance(value, dict):
            print(f"  {key}: dict with keys {list(value.keys())}")
            for subkey, subval in value.items():
                print(f"    - {subkey}: {subval}")
        else:
            print(f"  {key}: {value}")
    
    # FUNCTION 2: analyze_sliding_windows
    print("\n" + "="*80)
    print("FUNCTION 2: analyze_sliding_windows()")
    print("="*80)
    print("PURPOSE: Perform detailed sliding window analysis with quality metrics")
    
    window_size = 10 * sampling_rate
    stride = 1 * sampling_rate
    max_start = len(cleaned_signal) - window_size
    
    print("\nINPUTS:")
    print(f"  ecg_cleaned: numpy.ndarray shape {cleaned_signal.shape}")
    print(f"  r_peaks: numpy.ndarray shape {r_peaks.shape}")
    print(f"    - R-peak indices: {r_peaks}")
    print(f"  sampling_rate: int = {sampling_rate}")
    print(f"  window_size: int = {window_size} samples (10 seconds)")
    print(f"  stride: int = {stride} samples (1 second)")
    print(f"  max_start: int = {max_start}")
    
    print("\nEXECUTING...")
    sliding_result = analyze_sliding_windows(cleaned_signal, r_peaks, sampling_rate, 
                                           window_size, stride, max_start)
    
    print("\nOUTPUTS:")
    print(f"  Return type: {type(sliding_result)}")
    for key, value in sliding_result.items():
        if isinstance(value, pd.DataFrame):
            print(f"  {key}: pandas.DataFrame shape {value.shape}")
            if not value.empty:
                print(f"    - First window metrics: {dict(value.iloc[0])}")
        elif isinstance(value, list):
            print(f"  {key}: list with {len(value)} elements")
        elif isinstance(value, dict):
            print(f"  {key}: dict = {value}")
        else:
            print(f"  {key}: {value}")
    
    # FUNCTION 3: calculate_window_metrics (test on single window)
    print("\n" + "="*80)
    print("FUNCTION 3: calculate_window_metrics()")
    print("="*80)
    print("PURPOSE: Calculate quality metrics for a single 10-second window")
    print("CLASSIFICATION LOGIC:")
    print("  - REJECTED: kSQI < 3.0 (external artifacts/motion)")
    print("  - UNRELIABLE: mSQI < 0.5 (poor morphological quality)")
    print("  - GOOD: kSQI > 5.0 AND mSQI > 0.8 (optimal quality)")
    print("  - ACCEPTABLE: mSQI > 0.8 AND kSQI < 4.0 (baseline wander/stepping)")
    print("  - UNRELIABLE: all other cases")
    
    # Extract first window
    start_idx = 0
    end_idx = window_size
    window_number = 1
    segment = cleaned_signal[start_idx:end_idx]
    window_peaks = r_peaks[(r_peaks >= start_idx) & (r_peaks < end_idx)]
    relative_peaks = window_peaks - start_idx
    
    print("\nINPUTS:")
    print(f"  segment: numpy.ndarray shape {segment.shape}")
    print(f"    - Time range: {start_idx/sampling_rate:.1f}s to {end_idx/sampling_rate:.1f}s")
    print(f"    - Amplitude range: {np.min(segment):.3f} to {np.max(segment):.3f}")
    print(f"  relative_peaks: numpy.ndarray shape {relative_peaks.shape}")
    print(f"    - Peak indices in segment: {relative_peaks}")
    print(f"  sampling_rate: int = {sampling_rate}")
    print(f"  start_idx: int = {start_idx}")
    print(f"  end_idx: int = {end_idx}")
    print(f"  window_number: int = {window_number}")
    
    print("\nEXECUTING...")
    window_metrics = calculate_window_metrics(segment, relative_peaks, sampling_rate, 
                                            start_idx, end_idx, window_number)
    
    print("\nOUTPUTS:")
    print(f"  Return type: {type(window_metrics)}")
    print(f"  Metrics dictionary:")
    for key, value in window_metrics.items():
        print(f"    {key}: {value} ({type(value).__name__})")
    
    return assess_result, sliding_result, window_metrics

def create_focused_visualization(raw_signal, cleaned_signal, r_peaks, sampling_rate, channel):
    """Create focused visualization for CH3 only"""
    print(f"\n" + "="*60)
    print(f"CREATING FOCUSED VISUALIZATION FOR {channel}")
    print(f"="*60)
    
    # Run assessment to get window data
    assess_result = assess_ecg_quality(cleaned_signal, sampling_rate)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f'{channel} - Detailed Signal Quality Analysis', fontsize=16)
    
    time_array = np.arange(len(raw_signal)) / sampling_rate
    
    # Plot 1: Raw vs Cleaned Signal
    ax1 = axes[0, 0]
    ax1.plot(time_array, raw_signal, alpha=0.6, label='Raw Signal', color='gray', linewidth=1)
    ax1.plot(time_array, cleaned_signal, label='Cleaned Signal', color='blue', linewidth=1.5)
    ax1.scatter(time_array[r_peaks], cleaned_signal[r_peaks], color='red', s=40, alpha=0.8, label='R-peaks', zorder=5)
    ax1.set_title('Signal Processing: Raw → Cleaned + R-peak Detection')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude (mV)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Quality Windows Analysis
    ax2 = axes[0, 1]
    ax2.plot(time_array, cleaned_signal, color='lightblue', alpha=0.7, label='ECG Signal', linewidth=1)
    
    if assess_result and 'results_df' in assess_result and not assess_result['results_df'].empty:
        results_df = assess_result['results_df']
        
        for _, row in results_df.iterrows():
            start_time = row['start_time']
            end_time = row['end_time']
            status = row['status']
            
            color_map = {'GOOD': 'green', 'UNRELIABLE': 'orange', 'REJECTED': 'red'}
            color = color_map.get(status, 'gray')
            
            # Check if legend exists before accessing
            existing_labels = []
            if ax2.get_legend() is not None:
                existing_labels = [l.get_text() for l in ax2.get_legend().get_texts()]
            
            ax2.axvspan(start_time, end_time, alpha=0.3, color=color, 
                       label=status if status not in existing_labels else "")
        
        # Highlight best segment
        if 'best_segment_indices' in assess_result:
            best_start, best_end = assess_result['best_segment_indices']
            best_start_time = best_start / sampling_rate
            best_end_time = best_end / sampling_rate
            ax2.axvspan(best_start_time, best_end_time, alpha=0.5, color='gold', 
                       linestyle='--', linewidth=3, label='Best Segment')
    
    ax2.set_title('Quality Window Classification (10s windows, 1s stride)')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Amplitude (mV)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Quality Metrics Scatter
    ax3 = axes[1, 0]
    
    if assess_result and 'results_df' in assess_result and not assess_result['results_df'].empty:
        results_df = assess_result['results_df']
        window_centers = (results_df['start_time'] + results_df['end_time']) / 2
        
        scatter = ax3.scatter(window_centers, results_df['mSQI'], c=results_df['kSQI'], 
                             s=80, alpha=0.8, cmap='viridis', edgecolors='black', linewidth=0.5)
        
        # Add colorbar
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('kSQI (Kurtosis Score)')
        
        # Add threshold lines
        ax3.axhline(y=0.8, color='green', linestyle='--', alpha=0.7, label='Good Threshold (≥0.8)')
        ax3.axhline(y=0.5, color='red', linestyle='--', alpha=0.7, label='Unreliable Threshold (<0.5)')
        
        # Annotate best point
        best_idx = results_df['mSQI'].idxmax()
        best_row = results_df.loc[best_idx]
        best_center = (best_row['start_time'] + best_row['end_time']) / 2
        ax3.annotate(f'Best\nWindow {best_row["window"]}', 
                    xy=(best_center, best_row['mSQI']), 
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
    
    ax3.set_title('Quality Metrics: mSQI vs Time (colored by kSQI)')
    ax3.set_xlabel('Window Center Time (s)')
    ax3.set_ylabel('mSQI (Morphological Quality)')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 1)
    
    # Plot 4: Heart Rate and HRV
    ax4 = axes[1, 1]
    
    if assess_result and 'results_df' in assess_result and not assess_result['results_df'].empty:
        results_df = assess_result['results_df']
        window_centers = (results_df['start_time'] + results_df['end_time']) / 2
        
        # Plot HR
        ax4_hr = ax4
        ax4_hr.plot(window_centers, results_df['hr_bpm'], 'o-', color='red', linewidth=2, markersize=6, label='Heart Rate')
        ax4_hr.set_ylabel('Heart Rate (BPM)', color='red')
        ax4_hr.tick_params(axis='y', labelcolor='red')
        
        # Plot SDNN on secondary y-axis
        ax4_sdnn = ax4_hr.twinx()
        ax4_sdnn.plot(window_centers, results_df['sdnn_ms'], 's-', color='blue', linewidth=2, markersize=6, label='HRV (SDNN)')
        ax4_sdnn.set_ylabel('SDNN (ms)', color='blue')
        ax4_sdnn.tick_params(axis='y', labelcolor='blue')
        
        # Add legends
        ax4_hr.legend(loc='upper left')
        ax4_sdnn.legend(loc='upper right')
    
    ax4.set_title('Physiological Metrics: HR & HRV over Time')
    ax4.set_xlabel('Window Center Time (s)')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{channel}_focused_analysis.png', dpi=300, bbox_inches='tight')
    print(f"Detailed visualization saved as '{channel}_focused_analysis.png'")
    plt.show()

def main():
    """Main testing function - focused on CH3 only"""
    print("="*80)
    print("FOCUSED SIGNAL QUALITY TESTING - CH3 ONLY")
    print("="*80)
    
    # Load data
    filepath = "Device_6_Volts.txt"
    channels = ['CH3']  # Test only CH3
    duration = 30  # Analyze first 30 seconds
    
    try:
        df, metadata, sampling_rate = load_device_data(filepath, channels, duration)
    except FileNotFoundError:
        print(f"ERROR: File {filepath} not found in current directory")
        return
    except Exception as e:
        print(f"ERROR loading file: {e}")
        return
    
    # Test module info first
    print("\n" + "="*80)
    print("FUNCTION 0: get_module_info()")
    print("="*80)
    print("INPUT: None")
    module_info = test_module_info()
    print(f"OUTPUT: Dict with {len(module_info)} keys: {list(module_info.keys())}")
    
    # Process CH3 only
    channel = 'CH3'
    print(f"\n" + "="*80)
    print(f"PROCESSING CHANNEL {channel}")
    print(f"="*80)
    
    try:
        # Process channel data
        raw_signal, cleaned_signal, r_peaks, signals, info = process_channel_data(df, channel, sampling_rate)
        
        print(f"\nDATA PREPARATION SUMMARY:")
        print(f"  Raw signal shape: {raw_signal.shape}")
        print(f"  Cleaned signal shape: {cleaned_signal.shape}")
        print(f"  R-peaks array: {r_peaks}")
        print(f"  Number of R-peaks: {len(r_peaks)}")
        print(f"  Sampling rate: {sampling_rate} Hz")
        
        # Test each function individually with clear I/O documentation
        test_functions_with_io_documentation(cleaned_signal, r_peaks, sampling_rate, channel)
        
        # Create focused visualization
        create_focused_visualization(raw_signal, cleaned_signal, r_peaks, sampling_rate, channel)
        
    except Exception as e:
        print(f"ERROR processing channel {channel}: {e}")
        return
    
    print(f"\n" + "="*80)
    print(f"CH3 TESTING COMPLETED SUCCESSFULLY")
    print(f"="*80)

if __name__ == "__main__":
    main()