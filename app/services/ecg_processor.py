"""
ECG signal processing service using NeuroKit2.
Converted from analysis_ecg_signal.ipynb for production use.
"""
import re
from typing import Tuple, Dict, List, Optional
import numpy as np
import pandas as pd
import neurokit2 as nk
from ..models.ecg_models import ECGMetadata, ECGStatistics, SignalData, QualityAssessment, QualitySummary, QualityWindow
from ..signal_quality import assess_ecg_quality


class ECGProcessor:
    """Process and analyze ADS1298 ECG signals."""
    
    def __init__(self, sampling_rate: int = 500):
        """
        Initialize ECG processor.
        
        Args:
            sampling_rate: Sampling frequency in Hz
        """
        self.sampling_rate = sampling_rate
    
    def load_ads1298_file(
        self,
        filepath: str,
        channels: List[str] = None,
        duration: Optional[float] = None
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Load ADS1298 ECG data from text file.
        
        Args:
            filepath: Path to the .txt file
            channels: List of channel names to extract (default: ['CH2', 'CH3', 'CH4'])
            duration: Seconds of data to process (None = entire file)
        
        Returns:
            Tuple of (DataFrame with channels and time, metadata dict)
        """
        if channels is None:
            channels = ['CH2', 'CH3', 'CH4']
        
        # Read file
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
            elif re.match(r'\d+/\d+/\d+', line):
                metadata['datetime'] = line.strip()
            elif line.strip().startswith('CH1'):
                data_start_idx = i + 1
                break
        
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
        df['time'] = np.arange(len(df)) / self.sampling_rate
        
        # Apply duration limit if specified
        if duration is not None:
            max_samples = int(duration * self.sampling_rate)
            df = df.iloc[:max_samples]
        
        return df, metadata
    
    def process_ecg_signal(
        self,
        signal: np.ndarray
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process ECG signal using NeuroKit2.
        
        Args:
            signal: Raw ECG signal array
        
        Returns:
            Tuple of (processed signals DataFrame, info dict with R-peaks)
        """
        # Check minimum signal length (at least 5 seconds recommended for reliable segmentation)
        min_samples = int(5 * self.sampling_rate)
        signal_duration = len(signal) / self.sampling_rate
        
        if len(signal) < min_samples:
            raise ValueError(
                f"Signal too short for reliable analysis. "
                f"Current duration: {signal_duration:.1f}s. "
                f"Minimum recommended: 5.0s. "
                f"Please select a longer timeframe or upload a longer recording."
            )
        
        try:
            signals, info = nk.ecg_process(signal, sampling_rate=self.sampling_rate)
            return signals, info
        except Exception as e:
            # Catch NeuroKit2 segmentation errors
            if "segment" in str(e).lower() or "too small" in str(e).lower():
                raise ValueError(
                    f"Signal duration ({signal_duration:.1f}s) is too short for ECG analysis. "
                    f"Please select at least 5 seconds of data."
                )
            # Re-raise other errors
            raise
    
    def analyze_file(
        self,
        filepath: str,
        channels: List[str] = None,
        duration: Optional[float] = None,
        include_signals: bool = False
    ) -> Dict:
        """
        Complete ECG file analysis pipeline.
        
        Args:
            filepath: Path to ECG data file
            channels: Channels to consider for analysis
            duration: Duration to analyze in seconds
            include_signals: Whether to include full signal data
        
        Returns:
            Dictionary with metadata, statistics, and optional signal data
        """
        if channels is None:
            channels = ['CH2', 'CH3', 'CH4']
        
        # Load data
        df, metadata = self.load_ads1298_file(filepath, channels, duration)
        
        # Find available channels
        available_channels = [ch for ch in channels if ch in df.columns]
        if not available_channels:
            raise ValueError(f"None of the requested channels {channels} are available")
        
        # Use first available channel for processing
        ecg_channel = available_channels[0]
        ecg_signal = df[ecg_channel].values
        
        # Process ECG
        signals, info = self.process_ecg_signal(ecg_signal)
        r_peaks = info['ECG_R_Peaks']
        
        # Calculate statistics
        hr_mean = signals['ECG_Rate'].mean()
        hr_std = signals['ECG_Rate'].std()
        hr_min = signals['ECG_Rate'].min()
        hr_max = signals['ECG_Rate'].max()
        
        # Build metadata
        ecg_metadata = ECGMetadata(
            record_number=metadata.get('record_number'),
            datetime=metadata.get('datetime'),
            notes=metadata.get('notes'),
            gain=metadata.get('gain'),
            duration_seconds=float(df['time'].iloc[-1]),
            sample_count=len(df),
            channels_available=available_channels,
            processed_channel=ecg_channel
        )
        
        # Build statistics
        ecg_statistics = ECGStatistics(
            heart_rate_mean=float(hr_mean),
            heart_rate_std=float(hr_std),
            heart_rate_min=float(hr_min),
            heart_rate_max=float(hr_max),
            r_peaks_count=len(r_peaks),
            sampling_rate=self.sampling_rate
        )
        
        # Build response
        result = {
            'metadata': ecg_metadata,
            'statistics': ecg_statistics
        }
        
        # Optionally include signal data
        if include_signals:
            time_array = np.arange(len(signals)) / self.sampling_rate
            
            result['raw_signal'] = SignalData(
                time=df['time'].tolist(),
                values=df[ecg_channel].tolist()
            )
            
            result['cleaned_signal'] = SignalData(
                time=time_array.tolist(),
                values=signals['ECG_Clean'].tolist()
            )
            
            result['heart_rate_signal'] = SignalData(
                time=time_array.tolist(),
                values=signals['ECG_Rate'].tolist()
            )
            
            result['r_peak_times'] = time_array[r_peaks].tolist()
            result['r_peak_amplitudes'] = signals['ECG_Clean'].iloc[r_peaks].tolist()
            
            # Add signal quality assessment
            try:
                ecg_cleaned = signals['ECG_Clean'].values
                quality_result = assess_ecg_quality(ecg_cleaned, self.sampling_rate)
                results_df = quality_result.get('results_df', pd.DataFrame())
                
                # Convert DataFrame rows to QualityWindow objects
                quality_windows = []
                for _, row in results_df.iterrows():
                    quality_window = QualityWindow(
                        window=int(row['window']),
                        start_time=float(row['start_time']),
                        end_time=float(row['end_time']),
                        start_idx=int(row['start_idx']),
                        end_idx=int(row['end_idx']),
                        mSQI=float(row['mSQI']),
                        kSQI=float(row['kSQI']),
                        heart_rate=float(row['hr_bpm']),  # Use hr_bpm field
                        sdnn=float(row['sdnn_ms']),       # Use sdnn_ms field
                        status=str(row['status'])
                    )
                    quality_windows.append(quality_window)
                
                # Create summary
                summary_data = quality_result.get('summary', {})
                print("quality_summary:", summary_data)
                print("quality_results_df:", results_df)
                # Count acceptable windows (baseline wander cases)
                if {'status', 'mSQI', 'kSQI'}.issubset(results_df.columns):
                    acceptable_count = len(results_df[
                        (results_df['status'] == 'GOOD (Baseline Wander)') &
                        (results_df['mSQI'] > 0.8) &
                        (results_df['kSQI'] < 4.0)
                    ])
                else:
                    acceptable_count = 0

                total_windows = int(summary_data.get('total_windows', len(results_df)))
                good_windows = int(summary_data.get('good_windows', 0))
                rejected_windows = int(summary_data.get('rejected_windows', 0))
                unreliable_windows = int(summary_data.get('unreliable_windows', 0))
                good_percentage = float(summary_data.get('good_percentage', 0.0))
                overall_status = str(summary_data.get('status', 'FAILED' if total_windows == 0 else 'WARNING'))
                
                quality_summary = QualitySummary(
                    total_windows=total_windows,
                    good_windows=good_windows,
                    rejected_windows=rejected_windows,
                    unreliable_windows=unreliable_windows,
                    acceptable_windows=acceptable_count,
                    good_percentage=good_percentage,
                    status=overall_status
                )
                
                # Convert indices to times for frontend
                best_segment_indices = quality_result.get(
                    'best_segment_indices',
                    [0, min(len(ecg_cleaned), 10 * self.sampling_rate)]
                )
                best_start_time = best_segment_indices[0] / self.sampling_rate
                best_end_time = best_segment_indices[1] / self.sampling_rate
                
                bad_segment_times = []
                bad_segments = quality_result.get('bad_segments', [])
                for bad_segment in bad_segments:
                    bad_start_time = bad_segment[0] / self.sampling_rate
                    bad_end_time = bad_segment[1] / self.sampling_rate
                    bad_segment_times.append([bad_start_time, bad_end_time])
                
                # Create quality assessment object
                quality_assessment = QualityAssessment(
                    best_segment_indices=best_segment_indices,
                    best_segment_times=[best_start_time, best_end_time],
                    bad_segments=bad_segments,
                    bad_segment_times=bad_segment_times,
                    windows=quality_windows,
                    summary=quality_summary
                )
                
                result['quality_assessment'] = quality_assessment
                
            except Exception as e:
                print(f"Warning: Signal quality assessment failed: {e}")
                # Continue without quality assessment
        
        return result
