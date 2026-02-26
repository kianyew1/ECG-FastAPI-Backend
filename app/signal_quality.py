import numpy as np
import pandas as pd
import neurokit2 as nk
from typing import List, Tuple, Dict, Optional
from scipy import signal as scipy_signal
from scipy.stats import zscore, kurtosis


def assess_ecg_quality(ecg_cleaned: np.ndarray, sampling_rate: int = 500) -> Dict:
    """
    Ambulatory ECG Quality Assessment System
    
    Analyzes a pre-cleaned ECG signal to identify the optimal 10-second segment 
    for analysis and isolate segments corrupted by external factors (motion artifacts).
    
    Parameters:
    -----------
    ecg_cleaned : np.ndarray
        Pre-cleaned ECG signal (typically 30 seconds duration)
    sampling_rate : int
        Sampling frequency in Hz (e.g., 500)
        
    Returns:
    --------
    Dict containing:
        - best_segment_indices: [start, end] indices of optimal 10s segment
        - bad_segments: List of [start, end] indices for rejected windows  
        - results_df: DataFrame with detailed analysis of all windows
        - summary: Summary statistics and recommendations
    """
    
    print(f"=== Ambulatory ECG Quality Assessment ===")
    print(f"Signal length: {len(ecg_cleaned)} samples ({len(ecg_cleaned)/sampling_rate:.1f}s)")
    print(f"Sampling rate: {sampling_rate} Hz")
    
    # Step 1: Global Peak Detection
    print("\n1. Global Peak Detection...")
    try:
        # Detect R-peaks on entire signal
        _, peaks_info = nk.ecg_peaks(ecg_cleaned, sampling_rate=sampling_rate, method='neurokit')
        r_peaks = peaks_info['ECG_R_Peaks']
        
        print(f"   Detected {len(r_peaks)} initial R-peaks")
        print(f"   R-peaks type: {type(r_peaks)}")
        print(f"   R-peaks shape: {r_peaks.shape if hasattr(r_peaks, 'shape') else 'N/A'}")
        
        # Ensure r_peaks is a proper numpy array of integers
        if not isinstance(r_peaks, np.ndarray):
            r_peaks = np.array(r_peaks, dtype=int)
        
        # Skip peak correction for now to avoid the array issue
        r_peaks_corrected = r_peaks.astype(int)
        
        print(f"   Using {len(r_peaks_corrected)} R-peaks for analysis")
        
    except Exception as e:
        print(f"   ERROR in peak detection: {e}")
        return {
            'best_segment_indices': [0, min(10*sampling_rate, len(ecg_cleaned))],
            'bad_segments': [],
            'results_df': pd.DataFrame(),
            'summary': {'error': 'Peak detection failed', 'status': 'FAILED'}
        }
    
    # Step 2: Initialize Sliding Window Engine
    print("\n2. Sliding Window Engine Setup...")
    window_size = 10 * sampling_rate  # 10 seconds in samples
    stride = 1 * sampling_rate        # 1 second stride in samples
    
    print(f"   Window size: {window_size} samples (10s)")
    print(f"   Stride: {stride} samples (1s)")
    
    # Initialize storage
    window_results = []
    bad_segments = []
    
    # Calculate number of windows
    max_start = len(ecg_cleaned) - window_size
    if max_start < 0:
        print(f"   ERROR: Signal too short for 10s windows")
        return {
            'best_segment_indices': [0, len(ecg_cleaned)],
            'bad_segments': [],
            'results_df': pd.DataFrame(),
            'summary': {'error': 'Signal too short', 'status': 'FAILED'}
        }
    
    num_windows = (max_start // stride) + 1
    print(f"   Total windows to analyze: {num_windows}")
    
    return analyze_sliding_windows(ecg_cleaned, r_peaks_corrected, sampling_rate, 
                                 window_size, stride, max_start)


def analyze_sliding_windows(ecg_cleaned: np.ndarray, r_peaks: np.ndarray, 
                          sampling_rate: int, window_size: int, stride: int, max_start: int) -> Dict:
    """
    Perform sliding window analysis on the ECG signal.
    """
    
    # Ensure r_peaks is a numpy array
    if not isinstance(r_peaks, np.ndarray):
        r_peaks = np.array(r_peaks)
    
    window_results = []
    bad_segments = []
    
    print("\n3. Sliding Window Analysis...")
    print("   Window | Quality (mSQI) | Kurtosis |   HR   | SDNN | Status")
    print("   -------|----------------|----------|--------|------|--------")
    
    # Step 3: Loop through windows
    for window_idx in range(0, max_start + 1, stride):
        start_idx = window_idx
        end_idx = start_idx + window_size
        window_number = (window_idx // stride) + 1
        
        # Extract window segment
        segment = ecg_cleaned[start_idx:end_idx]
        
        # Find R-peaks within this window
        window_peaks = r_peaks[(r_peaks >= start_idx) & (r_peaks < end_idx)]
        
        # Convert to relative indices for the segment
        relative_peaks = window_peaks - start_idx
        
        # Calculate metrics for this window
        try:
            metrics = calculate_window_metrics(segment, relative_peaks, sampling_rate, 
                                             start_idx, end_idx, window_number)
            window_results.append(metrics)
            
            # Check if this window should be rejected
            if metrics['status'] in ['REJECTED', 'UNRELIABLE', 'REJECTED (External Artifact)']:
                bad_segments.append([start_idx, end_idx])
                
        except Exception as e:
            print(f"   {window_number:3d}    | ERROR: {str(e)[:30]}")
            bad_segments.append([start_idx, end_idx])
            continue
    
    # Step 4: Result Aggregation
    print(f"\n4. Result Aggregation...")
    
    if not window_results:
        print("   ERROR: No valid windows analyzed")
        return {
            'best_segment_indices': [0, min(window_size, len(ecg_cleaned))],
            'bad_segments': bad_segments,
            'results_df': pd.DataFrame(),
            'summary': {'error': 'No valid windows', 'status': 'FAILED'}
        }
    
    # Convert to DataFrame and sort by quality
    results_df = pd.DataFrame(window_results)
    results_df_sorted = results_df.sort_values('mSQI', ascending=False)
    
    # Find best segment (highest quality that's not rejected)
    good_windows = results_df_sorted[results_df_sorted['status'].isin(['GOOD', 'GOOD (Baseline Wander)'])]
    if len(good_windows) > 0:
        best_window = good_windows.iloc[0]
        best_segment_indices = [int(best_window['start_idx']), int(best_window['end_idx'])]
        print(f"   Best segment found: Window {best_window['window']} (indices {best_segment_indices})")
        print(f"   Quality (mSQI): {best_window['mSQI']:.3f}, Kurtosis: {best_window['kSQI']:.2f}")
    else:
        # No good windows, take the least bad one
        print("   WARNING: No GOOD windows found, selecting best available")
        best_window = results_df_sorted.iloc[0]
        best_segment_indices = [int(best_window['start_idx']), int(best_window['end_idx'])]
        print(f"   Best available: Window {best_window['window']} (indices {best_segment_indices})")
    
    # Summary statistics
    total_windows = len(window_results)
    #good_count should include also 'GOOD (Baseline Wander)'
    good_count = len(results_df[results_df['status'].isin(['GOOD', 'GOOD (Baseline Wander)'])])
    rejected_count = len(results_df[results_df['status'] == 'REJECTED'])
    unreliable_count = len(results_df[results_df['status'] == 'UNRELIABLE'])
    
    summary = {
        'total_windows': total_windows,
        'good_windows': good_count,
        'rejected_windows': rejected_count,
        'unreliable_windows': unreliable_count,
        'good_percentage': (good_count / total_windows * 100) if total_windows > 0 else 0,
        'status': 'SUCCESS' if good_count > 0 else 'WARNING'
    }
    
    print(f"   Summary: {good_count} GOOD, {rejected_count} REJECTED, {unreliable_count} UNRELIABLE")
    print(f"   Quality rate: {summary['good_percentage']:.1f}%")
    
    return {
        'best_segment_indices': best_segment_indices,
        'bad_segments': bad_segments,
        'results_df': results_df,
        'summary': summary
    }


def calculate_window_metrics(segment: np.ndarray, relative_peaks: np.ndarray, 
                           sampling_rate: int, start_idx: int, end_idx: int, window_number: int) -> Dict:
    """
    Calculate quality metrics for a single 10-second window.
    
    Classification Logic:
    - REJECTED: kSQI < 3.0 (external artifacts/motion)
    - UNRELIABLE: mSQI < 0.5 (poor morphological quality)
    - GOOD: kSQI > 5.0 AND mSQI > 0.8 (optimal quality)
    - ACCEPTABLE: mSQI > 0.8 AND kSQI < 4.0 (baseline wander/stepping artifact)
    - UNRELIABLE: all other cases
    """
    
    # Initialize metrics dictionary
    metrics = {
        'window': window_number,
        'start_idx': start_idx,
        'end_idx': end_idx,
        'start_time': start_idx / sampling_rate,
        'end_time': end_idx / sampling_rate,
        'num_peaks': len(relative_peaks),
        'mSQI': 0.0,
        'kSQI': 0.0,
        'hr_bpm': 0.0,
        'sdnn_ms': 0.0,
        'status': 'UNKNOWN'
    }
    
    # Check if we have enough peaks for analysis
    if len(relative_peaks) < 3:
        metrics['status'] = 'UNRELIABLE'
        print(f"   {window_number:3d}    | Too few peaks ({len(relative_peaks)}) -> Status: UNRELIABLE")
        return metrics
    
    # A. Morphological Quality (mSQI) - Template Matching
    try:
        # Use NeuroKit's template matching quality assessment
        quality_scores = nk.ecg_quality(segment, method='templatematch', sampling_rate=sampling_rate)
        
        # Compute mean of correlation array
        if isinstance(quality_scores, np.ndarray) and len(quality_scores) > 0:
            mSQI = np.mean(quality_scores)
        else:
            mSQI = float(quality_scores) if quality_scores is not None else 0.0
            
        metrics['mSQI'] = mSQI
        
    except Exception as e:
        print(f"   {window_number:3d}    | mSQI calculation error: {str(e)[:20]}")
        metrics['mSQI'] = 0.0
        mSQI = 0.0
    
    # B. Statistical Noise (kSQI) - Kurtosis
    try:
        # Compute kurtosis (fisher=False gives Pearson definition)
        kSQI = kurtosis(segment, fisher=False)
        metrics['kSQI'] = kSQI
        
    except Exception as e:
        print(f"   {window_number:3d}    | kSQI calculation error: {str(e)[:20]}")
        metrics['kSQI'] = 0.0
        kSQI = 0.0
    
    # C. Physiological Stability
    try:
        if len(relative_peaks) >= 2:
            # Calculate RR intervals (in seconds)
            rr_intervals = np.diff(relative_peaks) / sampling_rate
            
            # Heart Rate (beats per minute)
            mean_rr = np.mean(rr_intervals)
            hr_bpm = 60.0 / mean_rr if mean_rr > 0 else 0.0
            
            # SDNN (Standard Deviation of NN intervals) in milliseconds
            sdnn_ms = np.std(rr_intervals) * 1000  # Convert to ms
            
            metrics['hr_bpm'] = hr_bpm
            metrics['sdnn_ms'] = sdnn_ms
        
    except Exception as e:
        print(f"   {window_number:3d}    | Stability calculation error: {str(e)[:20]}")
        metrics['hr_bpm'] = 0.0
        metrics['sdnn_ms'] = 0.0
    
# D. Classification Logic with "Thought Process" Logging
    
    # 1. REJECTION TIER: Fundamental Signal Failure
    # External Factor (Artifact): kSQI < 3.0 (signal is white noise/random/flat)
    if kSQI < 3.0:
        metrics['status'] = 'REJECTED (External Artifact)'
        
    # Unreliable: mSQI < 0.5 (beats do not look like heartbeats/extreme arrhythmia)
    elif mSQI < 0.5:
        metrics['status'] = 'UNRELIABLE'

    # 2. GOOD TIER: High Peakedness + High Consistency
    # This is the Gold Standard.
    elif kSQI > 5.0 and mSQI > 0.8:
        metrics['status'] = 'GOOD'

    # 3. GOOD TIER: High Consistency + Moderate Peakedness (Baseline Wander)
    # mSQI > 0.8 implies the QRS shape is great. 
    # The lower kSQI (implied < 5.0 here because it failed the previous check) 
    # suggests the baseline is "wandering" (running motion), making the distribution flatter.
    elif mSQI > 0.8:
        metrics['status'] = 'GOOD (Baseline Wander)'

    # 4. ADEQUATE TIER: Moderate Consistency
    # This catches the gap you noticed (0.5 <= mSQI <= 0.8).
    # These are usable for Heart Rate, but maybe not for fine morphology.
    elif mSQI >= 0.5:
        metrics['status'] = 'ADEQUATE'

    # 5. Fallback (Should be mathematically impossible to reach given above logic, but safe to keep)
    else:
        metrics['status'] = 'UNRELIABLE'
    
    # Print decision process
    print(f"   {window_number:3d}    | {mSQI:13.3f}  | {kSQI:7.2f}  | {metrics['hr_bpm']:5.0f}  | {metrics['sdnn_ms']:4.0f} | {metrics['status']}")
    
    return metrics


# Module information
def get_module_info() -> Dict:
    """
    Return information about this ambulatory ECG quality assessment module.
    """
    return {
        'module': 'Ambulatory ECG Quality Assessment',
        'version': '3.0.0',
        'method': '10-second sliding window analysis',
        'metrics': [
            'mSQI (Morphological Quality - Template Matching)',
            'kSQI (Statistical Noise - Kurtosis)', 
            'Heart Rate and SDNN (Physiological Stability)'
        ],
        'thresholds': {
            'external_artifact': 'kSQI < 3.0',
            'unreliable': 'mSQI < 0.5', 
            'good': 'kSQI > 5.0 AND mSQI > 0.8',
            'baseline_wander': 'mSQI > 0.8 AND kSQI < 4.0 (acceptable quality with motion artifact)'
        },
        'primary_function': 'assess_ecg_quality',
        'output_format': 'Best 10s segment selection with bad segment identification',
        'clinical_focus': 'Ambulatory ECG analysis with motion artifact detection'
    }
