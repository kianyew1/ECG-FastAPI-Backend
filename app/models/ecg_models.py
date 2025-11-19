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


class ECGAnalysisResponse(BaseModel):
    """Complete ECG analysis result."""
    metadata: ECGMetadata
    statistics: ECGStatistics
    raw_signal: Optional[SignalData] = Field(None, description="Raw ECG signal data")
    cleaned_signal: Optional[SignalData] = Field(None, description="Cleaned ECG signal")
    heart_rate_signal: Optional[SignalData] = Field(None, description="Heart rate over time")
    r_peak_times: Optional[List[float]] = Field(None, description="R-peak time points (seconds)")
    r_peak_amplitudes: Optional[List[float]] = Field(None, description="R-peak amplitude values")


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
