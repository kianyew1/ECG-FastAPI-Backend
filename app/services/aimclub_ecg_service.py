"""
AimClub ECG Library Integration Service
Adapts 8-channel ECG data to work with aimclub's 12-lead ECG analysis library.
"""
from typing import Tuple, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from pathlib import Path

# AimClub ECG imports
try:
    import ECG.api as ecg_api
    from ECG.data_classes import ElevatedST, Diagnosis, RiskMarkers, Failed
    from ECG.ecghealthcheck.enums import ECGClass
    AIMCLUB_AVAILABLE = True
except ImportError:
    AIMCLUB_AVAILABLE = False
    ecg_api = None


class AimClubECGService:
    """Service for analyzing ECG data using the aimclub ECG library."""
    
    def __init__(self, sampling_rate: int = 500):
        """
        Initialize AimClub ECG service.
        
        Args:
            sampling_rate: Sampling frequency in Hz (aimclub requires 500 Hz)
        """
        if not AIMCLUB_AVAILABLE:
            raise ImportError(
                "AimClub ECG library not installed. Install with: "
                "pip install git+https://github.com/aimclub/ECG.git"
            )
        
        if sampling_rate != 500:
            raise ValueError("AimClub ECG library requires 500 Hz sampling rate")
        
        self.sampling_rate = sampling_rate
    
    def load_8channel_file(
        self,
        filepath: str,
        duration: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict[str, str]]:
        """
        Load 8-channel ECG data from text file.
        
        Args:
            filepath: Path to the .txt file
            duration: Seconds of data to process (None = entire file)
        
        Returns:
            Tuple of (8-channel data array, metadata dict)
        """
        # Read the file, skipping header rows
        data = pd.read_csv(filepath, sep='\t', skiprows=6, header=0)
        
        # Drop unnamed columns
        data = data.loc[:, ~data.columns.str.contains('^Unnamed')]
        
        # Extract metadata from file header
        metadata = {}
        with open(filepath, 'r') as f:
            lines = f.readlines()[:6]
            for line in lines:
                if 'Record #:' in line:
                    metadata['record_number'] = line.split(':')[1].strip()
                elif 'Notes' in line and ':' in line:
                    metadata['notes'] = lines[lines.index(line) + 1].strip()
        
        # Convert to numpy array and transpose to (channels, samples)
        ecg_data = data.values.T
        
        # Apply duration limit if specified
        if duration is not None:
            max_samples = int(duration * self.sampling_rate)
            ecg_data = ecg_data[:, :max_samples]
        
        return ecg_data, metadata
    
    def convert_8ch_to_12lead(self, ecg_8ch: np.ndarray) -> np.ndarray:
        """
        Convert 8-channel ECG to 12-lead format.
        
        The aimclub library expects 12-lead ECG format. This function:
        1. Uses the 8 available channels
        2. Duplicates channels 5-8 to fill positions 9-12
        
        Standard 12-lead order: I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6
        
        Args:
            ecg_8ch: 8-channel ECG data with shape (8, samples)
        
        Returns:
            12-lead ECG data with shape (12, samples)
        """
        if ecg_8ch.shape[0] != 8:
            raise ValueError(f"Expected 8 channels, got {ecg_8ch.shape[0]}")
        
        num_samples = ecg_8ch.shape[1]
        ecg_12_lead = np.zeros((12, num_samples))
        
        # Copy original 8 channels
        ecg_12_lead[:8, :] = ecg_8ch
        
        # Duplicate channels 5-8 to fill positions 9-12
        # This provides realistic signal data rather than zeros
        ecg_12_lead[8:12, :] = ecg_8ch[4:8, :]
        
        return ecg_12_lead
    
    def check_st_elevation(
        self,
        ecg_12_lead: np.ndarray,
        use_neural_network: bool = False
    ) -> Dict:
        """
        Check for ST-elevation in ECG signal.
        
        Args:
            ecg_12_lead: 12-lead ECG data (12, samples)
            use_neural_network: Use NN method instead of classic CV method
        
        Returns:
            Dictionary with status and explanation
        """
        if use_neural_network:
            result = ecg_api.check_ST_elevation_with_NN(ecg_12_lead)
        else:
            result = ecg_api.check_ST_elevation(ecg_12_lead, sampling_rate=self.sampling_rate)
        
        if isinstance(result, Failed):
            return {
                'success': False,
                'error': result.reason,
                'exception': str(result.exception) if result.exception else None
            }
        
        status, explanation = result
        
        response = {
            'success': True,
            'st_elevation_detected': status.value if hasattr(status, 'value') else str(status),
            'method': 'neural_network' if use_neural_network else 'classic_cv'
        }
        
        if use_neural_network:
            response['explanation'] = explanation.text
            response['has_gradcam'] = explanation.image is not None
        else:
            response['explanation'] = explanation.content
        
        return response
    
    def evaluate_risk_markers(self, ecg_12_lead: np.ndarray) -> Dict:
        """
        Evaluate MI risk markers (QTc, RA_V4, STE60_V3).
        
        Args:
            ecg_12_lead: 12-lead ECG data (12, samples)
        
        Returns:
            Dictionary with risk marker values
        """
        result = ecg_api.evaluate_risk_markers(ecg_12_lead, sampling_rate=self.sampling_rate)
        
        if isinstance(result, Failed):
            return {
                'success': False,
                'error': result.reason
            }
        
        return {
            'success': True,
            'QTc_ms': float(result.QTc),
            'RA_V4_mv': float(result.RA_V4),
            'STE60_V3_mv': float(result.Ste60_V3)
        }
    
    def diagnose_mi_vs_ber(
        self,
        ecg_12_lead: np.ndarray,
        use_tuned_formula: bool = False,
        use_neural_network: bool = False
    ) -> Dict:
        """
        Differential diagnosis for MI vs BER (Benign Early Repolarization).
        
        Args:
            ecg_12_lead: 12-lead ECG data (12, samples)
            use_tuned_formula: Use tuned formula for risk marker method
            use_neural_network: Use neural network methods instead
        
        Returns:
            Dictionary with diagnosis results
        """
        if use_neural_network:
            # Use NN methods
            ber_result = ecg_api.check_BER_with_NN(ecg_12_lead)
            mi_result = ecg_api.check_MI_with_NN(ecg_12_lead)
            
            response = {'success': True, 'method': 'neural_network'}
            
            if not isinstance(ber_result, Failed):
                ber_present, ber_explanation = ber_result
                response['ber_detected'] = ber_present
                response['ber_explanation'] = ber_explanation.text
            
            if not isinstance(mi_result, Failed):
                mi_present, mi_explanation = mi_result
                response['mi_detected'] = mi_present
                response['mi_explanation'] = mi_explanation.text
            
            return response
        else:
            # Use risk marker formula
            result = ecg_api.diagnose_with_risk_markers(
                ecg_12_lead,
                sampling_rate=self.sampling_rate,
                tuned=use_tuned_formula
            )
            
            if isinstance(result, Failed):
                return {
                    'success': False,
                    'error': result.reason
                }
            
            diagnosis, explanation = result
            
            return {
                'success': True,
                'method': 'risk_markers_tuned' if use_tuned_formula else 'risk_markers_default',
                'diagnosis': diagnosis.value if hasattr(diagnosis, 'value') else str(diagnosis),
                'explanation': explanation.content
            }
    
    def get_qrs_complex(self, ecg_12_lead: np.ndarray) -> Dict:
        """
        Detect QRS complex in ECG signal.
        
        Args:
            ecg_12_lead: 12-lead ECG data (12, samples)
        
        Returns:
            Dictionary with QRS detection results
        """
        result = ecg_api.get_qrs_complex(ecg_12_lead, sampling_rate=self.sampling_rate)
        
        if isinstance(result, Failed):
            return {
                'success': False,
                'error': result.reason
            }
        
        cleaned_signal, qrs_peaks = result
        
        # Summarize QRS peaks for each channel
        peaks_summary = []
        for channel_idx, channel_peaks in enumerate(qrs_peaks):
            if channel_peaks:
                channel_info = {'channel': channel_idx, 'waves': {}}
                for wave_name, peaks in channel_peaks.items():
                    if peaks is not None:
                        valid_peaks = [p for p in peaks if not np.isnan(p)]
                        channel_info['waves'][wave_name] = {
                            'count': len(valid_peaks),
                            'peaks': valid_peaks[:10]  # Limit for response size
                        }
                peaks_summary.append(channel_info)
        
        return {
            'success': True,
            'cleaned_signal_shape': cleaned_signal.shape,
            'qrs_peaks_detected': len(peaks_summary),
            'peaks_summary': peaks_summary
        }
    
    def analyze_ecg_complete(
        self,
        filepath: str,
        duration: Optional[float] = None,
        include_nn_analysis: bool = True
    ) -> Dict:
        """
        Complete ECG analysis pipeline using aimclub library.
        
        Args:
            filepath: Path to 8-channel ECG file
            duration: Duration to analyze in seconds (minimum 5s recommended)
            include_nn_analysis: Include neural network-based analysis
        
        Returns:
            Comprehensive analysis results dictionary
        """
        # Load 8-channel data
        ecg_8ch, metadata = self.load_8channel_file(filepath, duration)
        
        # Convert to 12-lead format
        ecg_12_lead = self.convert_8ch_to_12lead(ecg_8ch)
        
        # Calculate duration
        signal_duration = ecg_12_lead.shape[1] / self.sampling_rate
        
        if signal_duration < 5.0:
            return {
                'success': False,
                'error': f'Signal too short ({signal_duration:.2f}s). Minimum 5s required.'
            }
        
        results = {
            'success': True,
            'metadata': metadata,
            'signal_info': {
                'original_channels': 8,
                'converted_leads': 12,
                'samples': ecg_12_lead.shape[1],
                'duration_seconds': signal_duration,
                'sampling_rate': self.sampling_rate
            }
        }
        
        # ST-Elevation Detection (Classic)
        st_classic = self.check_st_elevation(ecg_12_lead, use_neural_network=False)
        results['st_elevation_classic'] = st_classic
        
        # ST-Elevation Detection (Neural Network)
        if include_nn_analysis:
            st_nn = self.check_st_elevation(ecg_12_lead, use_neural_network=True)
            results['st_elevation_nn'] = st_nn
        
        # Risk Markers
        risk_markers = self.evaluate_risk_markers(ecg_12_lead)
        results['risk_markers'] = risk_markers
        
        # Differential Diagnosis (Risk Markers)
        diagnosis_default = self.diagnose_mi_vs_ber(ecg_12_lead, use_tuned_formula=False)
        results['diagnosis_risk_markers'] = diagnosis_default
        
        # Differential Diagnosis (Neural Network)
        if include_nn_analysis:
            diagnosis_nn = self.diagnose_mi_vs_ber(ecg_12_lead, use_neural_network=True)
            results['diagnosis_nn'] = diagnosis_nn
        
        # QRS Complex Detection
        qrs_results = self.get_qrs_complex(ecg_12_lead)
        results['qrs_complex'] = qrs_results
        
        return results


def is_aimclub_available() -> bool:
    """Check if aimclub ECG library is available."""
    return AIMCLUB_AVAILABLE
