"""
Pydantic models for ECG data structures and API request/response schemas.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ECGMetadata(BaseModel):
    """Metadata extracted from ADS1298 ECG file."""
    record_number: Optional[str] = Field(None, description="Recording identifier")
    datetime: Optional[str] = Field(None, description="Recording timestamp")
    notes: Optional[str] = Field(None, description="Recording notes")
    gain: Optional[str] = Field(None, description="Amplifier gain setting")
    duration_seconds: float = Field(..., description="Recording duration in seconds")
    sample_count: int = Field(..., description="Number of samples")
    channels_available: List[str] = Field(..., description="Available channel names")
    processed_channel: str = Field(..., description="Channel used for ECG analysis")


class ECGStatistics(BaseModel):
    """ECG analysis statistics and heart rate metrics."""
    heart_rate_mean: float = Field(..., description="Mean heart rate (bpm)")
    heart_rate_std: float = Field(..., description="Heart rate standard deviation (bpm)")
    heart_rate_min: float = Field(..., description="Minimum heart rate (bpm)")
    heart_rate_max: float = Field(..., description="Maximum heart rate (bpm)")
    r_peaks_count: int = Field(..., description="Number of R-peaks detected")
    sampling_rate: int = Field(..., description="Sampling rate (Hz)")


class SignalData(BaseModel):
    """Time-series signal data for plotting."""
    time: List[float] = Field(..., description="Time points (seconds)")
    values: List[float] = Field(..., description="Signal amplitude values")


class QualitySummary(BaseModel):
    """Summary of ECG quality assessment."""
    total_windows: int = Field(..., description="Total number of analyzed windows")
    good_windows: int = Field(..., description="Number of good quality windows")
    rejected_windows: int = Field(..., description="Number of rejected windows")
    unreliable_windows: int = Field(..., description="Number of unreliable windows")
    acceptable_windows: int = Field(0, description="Number of acceptable windows (baseline wander)")
    good_percentage: float = Field(..., description="Percentage of good quality windows")
    status: str = Field(..., description="Overall assessment status")


class QualityWindow(BaseModel):
    """Individual quality assessment window results."""
    window: int = Field(..., description="Window number")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    start_idx: int = Field(..., description="Start sample index")
    end_idx: int = Field(..., description="End sample index") 
    mSQI: float = Field(..., description="Morphological Signal Quality Index")
    kSQI: float = Field(..., description="Kurtosis Signal Quality Index")
    heart_rate: float = Field(..., description="Mean heart rate in window")
    sdnn: float = Field(..., description="SDNN in window")
    status: str = Field(..., description="Quality classification")


class QualityAssessment(BaseModel):
    """ECG signal quality assessment results."""
    best_segment_indices: List[int] = Field(..., description="[start, end] indices of best 10s segment")
    best_segment_times: List[float] = Field(..., description="[start, end] times of best segment in seconds")
    bad_segments: List[List[int]] = Field(..., description="List of [start, end] indices for rejected windows")
    bad_segment_times: List[List[float]] = Field(..., description="List of [start, end] times for rejected windows")
    windows: List[QualityWindow] = Field(..., description="Detailed results for all analyzed windows")
    summary: QualitySummary = Field(..., description="Summary statistics")


class ECGAnalysisResponse(BaseModel):
    """Complete ECG analysis result."""
    metadata: ECGMetadata
    statistics: ECGStatistics
    raw_signal: Optional[SignalData] = Field(None, description="Raw ECG signal data")
    cleaned_signal: Optional[SignalData] = Field(None, description="Cleaned ECG signal")
    heart_rate_signal: Optional[SignalData] = Field(None, description="Heart rate over time")
    r_peak_times: Optional[List[float]] = Field(None, description="R-peak time points (seconds)")
    r_peak_amplitudes: Optional[List[float]] = Field(None, description="R-peak amplitude values")
    quality_assessment: Optional[QualityAssessment] = Field(None, description="Signal quality assessment")


class ECGAnalysisRequest(BaseModel):
    """Request parameters for ECG analysis."""
    channels: List[str] = Field(["CH2", "CH3", "CH4"], description="Channels to consider")
    duration: Optional[float] = Field(None, description="Duration to process in seconds (None = all)")
    sampling_rate: int = Field(500, description="Sampling rate in Hz")
    include_signals: bool = Field(False, description="Include full signal data in response")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
