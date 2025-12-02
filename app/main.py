"""
FastAPI application for ECG signal processing.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

from .config import settings
from .models.ecg_models import (
    ECGAnalysisResponse,
    HealthResponse,
)
from .services.ecg_processor import ECGProcessor
from .services.aimclub_ecg_service import AimClubECGService, is_aimclub_available

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microservice for analyzing ADS1298 ECG data using NeuroKit2"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
os.makedirs(settings.temp_dir, exist_ok=True)


@app.get("/api", response_model=HealthResponse)
async def root():
    """Root endpoint with service information."""
    return HealthResponse(
        status="running",
        version=settings.app_version
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version
    )


@app.post("/api/analyze", response_model=ECGAnalysisResponse)
async def analyze_ecg(
    file: UploadFile = File(..., description="ADS1298 ECG data file (.txt)"),
    duration: Optional[float] = Form(None, description="Duration to process (seconds)"),
    channels: Optional[str] = Form(None, description="Comma-separated channel names (e.g., 'CH2,CH3,CH4')"),
    include_signals: bool = Form(False, description="Include full signal data in response"),
    sampling_rate: int = Form(500, description="Sampling rate in Hz")
):
    """
    Analyze uploaded ECG file and return comprehensive statistics.
    
    Args:
        file: Uploaded .txt file containing ADS1298 ECG data
        duration: Optional duration limit in seconds (None = entire file)
        channels: Comma-separated channel names to analyze
        include_signals: Whether to include time-series signal data
        sampling_rate: Sampling frequency in Hz
    
    Returns:
        ECGAnalysisResponse with metadata, statistics, and optional signal data
    """
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .txt files are supported."
        )
    
    # Check file size
    file_size_mb = 0
    temp_file_path = None
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            mode='wb',
            delete=False,
            suffix='.txt',
            dir=settings.temp_dir
        ) as temp_file:
            content = await file.read()
            file_size_mb = len(content) / (1024 * 1024)
            
            if file_size_mb > settings.max_upload_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                )
            
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing file: {file.filename} ({file_size_mb:.2f}MB)")
        
        # Parse channels
        channel_list = (
            [ch.strip() for ch in channels.split(',')]
            if channels
            else settings.default_channels
        )
        
        # Validate duration
        if duration and duration > settings.max_duration_seconds:
            raise HTTPException(
                status_code=400,
                detail=f"Duration exceeds maximum of {settings.max_duration_seconds} seconds"
            )
        
        # Create processor with requested sampling rate
        processor = ECGProcessor(sampling_rate=sampling_rate)
        
        # Process ECG file
        result = processor.analyze_file(
            filepath=temp_file_path,
            channels=channel_list,
            duration=duration,
            include_signals=include_signals
        )
        
        logger.info(
            f"Analysis complete: {result['metadata'].processed_channel}, "
            f"HR: {result['statistics'].heart_rate_mean:.1f} bpm, "
            f"R-peaks: {result['statistics'].r_peaks_count}"
        )
        
        return ECGAnalysisResponse(**result)
    
    except ValueError as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for uncaught errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


@app.post("/api/analyze-aimclub")
async def analyze_ecg_aimclub(
    file: UploadFile = File(..., description="ADS1298 ECG data file (.txt) - 8 channels"),
    duration: Optional[float] = Form(None, description="Duration to process (seconds, min 5s)"),
    include_nn: bool = Form(True, description="Include neural network analysis")
):
    """
    Analyze uploaded 8-channel ECG file using aimclub ECG library.
    
    This endpoint converts your 8-channel data to 12-lead format and performs:
    - ST-elevation detection (classic CV and neural network)
    - Risk marker evaluation (QTc, RA_V4, STE60_V3)
    - Differential diagnosis (MI vs BER)
    - QRS complex detection
    
    Args:
        file: Uploaded .txt file with 8-channel ECG data
        duration: Duration to analyze (minimum 5 seconds recommended)
        include_nn: Include neural network-based analysis
    
    Returns:
        Comprehensive analysis using aimclub ECG library
    """
    if not is_aimclub_available():
        raise HTTPException(
            status_code=503,
            detail="AimClub ECG library not installed. Install with: pip install git+https://github.com/aimclub/ECG.git"
        )
    
    # Validate file type
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .txt files are supported."
        )
    
    temp_file_path = None
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            mode='wb',
            delete=False,
            suffix='.txt',
            dir=settings.temp_dir
        ) as temp_file:
            content = await file.read()
            file_size_mb = len(content) / (1024 * 1024)
            
            if file_size_mb > settings.max_upload_size_mb:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                )
            
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        logger.info(f"Processing file with aimclub: {file.filename} ({file_size_mb:.2f}MB)")
        
        # Validate duration
        if duration and duration < 5.0:
            raise HTTPException(
                status_code=400,
                detail="Duration must be at least 5 seconds for aimclub analysis"
            )
        
        # Create aimclub service (requires 500 Hz)
        aimclub_service = AimClubECGService(sampling_rate=500)
        
        # Run complete analysis
        result = aimclub_service.analyze_ecg_complete(
            filepath=temp_file_path,
            duration=duration,
            include_nn_analysis=include_nn
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Analysis failed'))
        
        logger.info(
            f"AimClub analysis complete: {result['signal_info']['duration_seconds']:.2f}s, "
            f"{result['signal_info']['samples']} samples"
        )
        
        return JSONResponse(content=result)
    
    except ValueError as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for uncaught errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )


# Mount static files (frontend) - must be last to catch all remaining routes
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_path}")
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.port,  # Use port property that checks PORT env variable
        reload=settings.debug
    )