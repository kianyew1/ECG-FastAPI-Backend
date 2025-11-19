"""
ECG signal processing service using NeuroKit2.
Converted from analysis_ecg_signal.ipynb for production use.
"""
import re
from typing import Tuple, Dict, List, Optional
import numpy as np
import pandas as pd
import neurokit2 as nk
from ..models.ecg_models import ECGMetadata, ECGStatistics, SignalData


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
        signals, info = nk.ecg_process(signal, sampling_rate=self.sampling_rate)
        return signals, info
    
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
        
        return result
