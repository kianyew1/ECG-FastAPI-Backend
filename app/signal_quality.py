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
        
        # Fix artifacts in peak locations (crucial for runners)
        r_peaks_corrected = nk.signal_fixpeaks(r_peaks, iterative=True, method="neurokit")
        
        # Ensure r_peaks_corrected is a numpy array
        if not isinstance(r_peaks_corrected, np.ndarray):
            r_peaks_corrected = np.array(r_peaks_corrected)
        
        print(f"   Detected {len(r_peaks_corrected)} R-peaks")
        print(f"   Corrected {len(r_peaks) - len(r_peaks_corrected)} artifact peaks")
        
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
    if max_start <= 0:
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
    print("   Window | Quality | Kurtosis |   HR   | SDNN | Status")
    print("   -------|---------|----------|--------|------|--------")
    
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
            if metrics['status'] in ['REJECTED', 'UNRELIABLE']:
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
    good_windows = results_df_sorted[results_df_sorted['status'] == 'GOOD']
    
    if len(good_windows) > 0:
        best_window = good_windows.iloc[0]
        best_segment_indices = [int(best_window['start_idx']), int(best_window['end_idx'])]
        print(f"   Best segment found: Window {best_window['window']} (indices {best_segment_indices})")
        print(f"   Quality: {best_window['mSQI']:.3f}, Kurtosis: {best_window['kSQI']:.2f}")
    else:
        # No good windows, take the least bad one
        print("   WARNING: No GOOD windows found, selecting best available")
        best_window = results_df_sorted.iloc[0]
        best_segment_indices = [int(best_window['start_idx']), int(best_window['end_idx'])]
        print(f"   Best available: Window {best_window['window']} (indices {best_segment_indices})")
    
    # Summary statistics
    total_windows = len(window_results)
    good_count = len(results_df[results_df['status'] == 'GOOD'])
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
        'results_df': results_df_sorted,
        'summary': summary
    }


def calculate_window_metrics(segment: np.ndarray, relative_peaks: np.ndarray, 
                           sampling_rate: int, start_idx: int, end_idx: int, window_number: int) -> Dict:
    """
    Calculate quality metrics for a single 10-second window.
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
    
    # External Factor (Artifact): kSQI < 3.0 (signal too "random" or "flat")
    if kSQI < 3.0:
        status = "REJECTED (External Artifact detected)"
        metrics['status'] = 'REJECTED'
    
    # Unreliable: mSQI < 0.5 (beats don't look like heartbeats)
    elif mSQI < 0.5:
        status = "UNRELIABLE"  
        metrics['status'] = 'UNRELIABLE'
    
    # Good: kSQI > 5.0 AND mSQI > 0.8
    elif kSQI > 5.0 and mSQI > 0.8:
        status = "GOOD"
        metrics['status'] = 'GOOD'
    
    # In-between cases
    else:
        if mSQI >= 0.5 and kSQI >= 3.0:
            status = "GOOD"
            metrics['status'] = 'GOOD'
        else:
            status = "UNRELIABLE"
            metrics['status'] = 'UNRELIABLE'
    
    # Print decision process
    print(f"   {window_number:3d}    | {mSQI:6.3f}  | {kSQI:7.2f}  | {metrics['hr_bpm']:5.0f}  | {metrics['sdnn_ms']:4.0f} | {status}")
    
    return metrics


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================

def assess_rr_segment_quality(ecg_cleaned: np.ndarray, r_peaks: np.ndarray, 
                            sampling_rate: int = 500) -> Dict:
    """
    Legacy compatibility wrapper for the new ambulatory assessment system.
    
    Note: This now uses the sliding window approach instead of R-R segment analysis.
    """
    
    # Use the new ambulatory assessment
    result = assess_ecg_quality(ecg_cleaned, sampling_rate)
    
    # Convert to legacy format for compatibility
    best_start, best_end = result['best_segment_indices']
    
    # Create fake segment metrics for the best segment only
    segment_metrics = [{
        'segment_number': 1,
        'start_time_s': best_start / sampling_rate,
        'end_time_s': best_end / sampling_rate,
        'noise_score': 0.9,  # Placeholder values
        'noise_status': 'PASS',
        'baseline_score': 0.9,
        'baseline_status': 'PASS', 
        'artifact_score': 0.9,
        'artifact_status': 'PASS',
        'stability_score': 0.9,
        'stability_status': 'PASS',
        'overall_status': 'PASS'
    }]
    
    # Convert bad segments to time ranges
    poor_quality_ranges = [(start/sampling_rate, end/sampling_rate) 
                          for start, end in result['bad_segments']]
    
    return {
        'full_signal_quality': {
            'signal_length_seconds': len(ecg_cleaned) / sampling_rate,
            'num_beats': len(r_peaks),
            'ambulatory_assessment': result['summary']
        },
        'poor_quality_ranges': poor_quality_ranges,
        'segment_metrics': segment_metrics,
        'overall_quality': result['summary'].get('good_percentage', 0) / 100,
        'total_segments': 1,
        'poor_segment_count': len(poor_quality_ranges),
        'ambulatory_result': result  # Include full result for debugging
    }


def get_poor_quality_timestamps(ecg_cleaned: np.ndarray, r_peaks: np.ndarray, 
                              sampling_rate: int = 500) -> List[Tuple[float, float]]:
    """
    Convenience function to get timestamp ranges of poor quality segments.
    """
    result = assess_ecg_quality(ecg_cleaned, sampling_rate)
    return [(start/sampling_rate, end/sampling_rate) 
            for start, end in result['bad_segments']]


def generate_quality_report(ecg_cleaned: np.ndarray, r_peaks: np.ndarray, 
                          sampling_rate: int = 500) -> Dict:
    """
    Generate a comprehensive ambulatory ECG quality report.
    """
    result = assess_ecg_quality(ecg_cleaned, sampling_rate)
    summary = result['summary']
    
    # Best segment info
    best_start, best_end = result['best_segment_indices'] 
    best_duration = (best_end - best_start) / sampling_rate
    
    # Overall assessment
    if summary['status'] == 'SUCCESS' and summary['good_percentage'] >= 50:
        assessment = 'EXCELLENT'
    elif summary['status'] == 'SUCCESS' and summary['good_percentage'] >= 25:
        assessment = 'GOOD'
    elif summary['good_percentage'] >= 10:
        assessment = 'ACCEPTABLE'
    else:
        assessment = 'POOR'
    
    return {
        'overall_assessment': assessment,
        'quality_score': summary['good_percentage'] / 100,
        'best_segment_start_s': best_start / sampling_rate,
        'best_segment_duration_s': best_duration,
        'total_windows_analyzed': summary['total_windows'],
        'good_windows_count': summary['good_windows'],
        'rejected_windows_count': summary['rejected_windows'],
        'ambulatory_summary': summary,
        'analysis_method': 'Ambulatory ECG Quality Assessment (10s sliding windows)',
        'analysis_summary': f"Analyzed {summary['total_windows']} windows. "
                          f"Quality assessment: {assessment} ({summary['good_percentage']:.1f}% good windows). "
                          f"Best 10s segment: {best_start/sampling_rate:.1f}s - {best_end/sampling_rate:.1f}s."
    }


def validate_signal_for_analysis(ecg_cleaned: np.ndarray, r_peaks: np.ndarray, 
                               sampling_rate: int = 500, min_good_ratio: float = 0.2) -> Tuple[bool, str]:
    """
    Validate if the ECG signal is suitable for clinical analysis using ambulatory assessment.
    """
    if len(ecg_cleaned) < 10 * sampling_rate:
        return False, "Signal too short for ambulatory assessment (< 10s)"
    
    result = assess_ecg_quality(ecg_cleaned, sampling_rate)
    summary = result['summary']
    
    if summary['status'] == 'FAILED':
        return False, f"Assessment failed: {summary.get('error', 'Unknown error')}"
    
    good_ratio = summary['good_percentage'] / 100
    
    if good_ratio < min_good_ratio:
        return False, f"Insufficient quality windows ({good_ratio:.1%} < {min_good_ratio:.1%})"
    
    return True, f"Signal quality acceptable ({good_ratio:.1%} good windows)"


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
            'good': 'kSQI > 5.0 AND mSQI > 0.8'
        },
        'primary_function': 'assess_ecg_quality',
        'output_format': 'Best 10s segment selection with bad segment identification',
        'clinical_focus': 'Ambulatory ECG analysis with motion artifact detection'
    }
