# AimClub ECG Library Integration Guide

This guide explains how to use the aimclub ECG library with your 8-channel ECG data in the Python ECG Backend.

## Overview

The aimclub ECG library is designed for 12-lead ECG analysis, but your device captures 8 channels. This integration:

1. **Loads your 8-channel data** from `.txt` files
2. **Converts to 12-lead format** by duplicating channels 5-8 to fill leads 9-12
3. **Runs comprehensive ECG analysis** including:
   - ST-elevation detection (classic CV and neural network methods)
   - Risk marker evaluation (QTc, RA_V4, STE60_V3)
   - Differential diagnosis (MI vs BER)
   - QRS complex detection

## Installation

### 1. Install AimClub ECG Library

```bash
# Activate your virtual environment first
source .venv/bin/activate

# Install aimclub ECG from GitHub
pip install git+https://github.com/aimclub/ECG.git

# Install additional dependencies
pip install torch opencv-python grad-cam pillow
```

### 2. Verify Installation

```bash
python test_aimclub_integration.py
```

This will test the integration with your `Device_1_Volts.txt` file.

## Usage

### Option 1: Python API (Direct)

```python
from app.services.aimclub_ecg_service import AimClubECGService

# Initialize service (requires 500 Hz)
service = AimClubECGService(sampling_rate=500)

# Run complete analysis
results = service.analyze_ecg_complete(
    filepath='Device_1_Volts.txt',
    duration=10.0,  # Analyze first 10 seconds
    include_nn_analysis=True
)

# Access results
print(f"ST-Elevation: {results['st_elevation_classic']['st_elevation_detected']}")
print(f"QTc: {results['risk_markers']['QTc_ms']:.2f} ms")
print(f"Diagnosis: {results['diagnosis_risk_markers']['diagnosis']}")
```

### Option 2: FastAPI Endpoint

Start your server:

```bash
python -m app.main
```

Send a request:

```bash
curl -X POST "http://localhost:8080/api/analyze-aimclub" \
  -F "file=@Device_1_Volts.txt" \
  -F "duration=10.0" \
  -F "include_nn=true"
```

Or use Python:

```python
import requests

with open('Device_1_Volts.txt', 'rb') as f:
    response = requests.post(
        'http://localhost:8080/api/analyze-aimclub',
        files={'file': f},
        data={'duration': 10.0, 'include_nn': True}
    )

results = response.json()
print(results)
```

## API Response Structure

```json
{
  "success": true,
  "metadata": {
    "record_number": "1",
    "notes": "gain 6 zorye running"
  },
  "signal_info": {
    "original_channels": 8,
    "converted_leads": 12,
    "samples": 5000,
    "duration_seconds": 10.0,
    "sampling_rate": 500
  },
  "st_elevation_classic": {
    "success": true,
    "st_elevation_detected": "NORMAL",
    "method": "classic_cv",
    "explanation": "No ST elevation detected"
  },
  "st_elevation_nn": {
    "success": true,
    "st_elevation_detected": "NORMAL",
    "method": "neural_network",
    "explanation": "Neural network detected no ST elevation",
    "has_gradcam": true
  },
  "risk_markers": {
    "success": true,
    "QTc_ms": 412.5,
    "RA_V4_mv": 1.234,
    "STE60_V3_mv": 0.056
  },
  "diagnosis_risk_markers": {
    "success": true,
    "method": "risk_markers_default",
    "diagnosis": "NORMAL",
    "explanation": "Risk markers within normal range"
  },
  "diagnosis_nn": {
    "success": true,
    "method": "neural_network",
    "ber_detected": false,
    "ber_explanation": "No benign early repolarization detected",
    "mi_detected": false,
    "mi_explanation": "No myocardial infarction detected"
  },
  "qrs_complex": {
    "success": true,
    "cleaned_signal_shape": [12, 5000],
    "qrs_peaks_detected": 12,
    "peaks_summary": [...]
  }
}
```

## Key Features

### 1. ST-Elevation Detection

**Classic CV Method**: Uses computer vision algorithms to detect ST-elevation

```python
st_classic = service.check_st_elevation(ecg_12_lead, use_neural_network=False)
```

**Neural Network Method**: Uses deep learning with GradCAM visualization

```python
st_nn = service.check_st_elevation(ecg_12_lead, use_neural_network=True)
```

### 2. Risk Markers

Evaluates three key cardiac risk markers:

- **QTc**: Corrected QT interval (normal: 350-450 ms)
- **RA_V4**: R-wave amplitude in lead V4
- **STE60_V3**: ST elevation at 60ms in lead V3

```python
risk_markers = service.evaluate_risk_markers(ecg_12_lead)
print(f"QTc: {risk_markers['QTc_ms']:.2f} ms")
```

### 3. Differential Diagnosis (MI vs BER)

**Risk Marker Method**: Uses formula-based approach

```python
diagnosis = service.diagnose_mi_vs_ber(
    ecg_12_lead,
    use_tuned_formula=True,
    use_neural_network=False
)
```

**Neural Network Method**: Separate detection of MI and BER

```python
diagnosis_nn = service.diagnose_mi_vs_ber(
    ecg_12_lead,
    use_neural_network=True
)
```

### 4. QRS Complex Detection

Detects P, Q, R, S, T waves across all leads:

```python
qrs_result = service.get_qrs_complex(ecg_12_lead)
cleaned_signal = qrs_result['cleaned_signal_shape']
peaks = qrs_result['peaks_summary']
```

## 8-Channel to 12-Lead Conversion

Your device captures 8 channels (CH1-CH8), but aimclub expects 12 leads. The conversion:

```
12-Lead Standard:    I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6
Your 8 Channels:     CH1, CH2, CH3, CH4, CH5, CH6, CH7, CH8

Conversion Mapping:
├─ Leads 0-7:  Direct copy of CH1-CH8
└─ Leads 8-11: Duplicated from CH5-CH8 (provides realistic signal data)
```

This is handled automatically by the service:

```python
ecg_12_lead = service.convert_8ch_to_12lead(ecg_8ch)
```

## Requirements

- **Sampling Rate**: 500 Hz (required by aimclub)
- **Minimum Duration**: 5 seconds (recommended for reliable analysis)
- **Data Format**: Tab-delimited `.txt` file with 8 channels

## Comparison with NeuroKit2

Your project uses both libraries for different purposes:

| Feature              | NeuroKit2                      | AimClub ECG                           |
| -------------------- | ------------------------------ | ------------------------------------- |
| **Primary Use**      | General ECG processing         | Clinical diagnosis (MI, BER)          |
| **Lead Format**      | Flexible (single/multi-lead)   | Requires 12-lead                      |
| **Key Features**     | HRV, peak detection, filtering | ST-elevation, risk markers, diagnosis |
| **Analysis Methods** | Signal processing              | CV + Deep Learning                    |
| **Output**           | Time-series metrics            | Clinical interpretations              |

**Recommendation**: Use both!

- **NeuroKit2** (`/api/analyze`): For general signal quality, HRV, and peak detection
- **AimClub** (`/api/analyze-aimclub`): For clinical diagnosis and ST-elevation detection

## Troubleshooting

### Library Not Found

```
ImportError: No module named 'ECG'
```

**Solution**: Install aimclub ECG library

```bash
pip install git+https://github.com/aimclub/ECG.git
```

### Signal Too Short

```
Signal too short (3.5s). Minimum 5s required.
```

**Solution**: Increase duration parameter or use longer recording

```python
results = service.analyze_ecg_complete(filepath='data.txt', duration=10.0)
```

### Wrong Sampling Rate

```
ValueError: AimClub ECG library requires 500 Hz sampling rate
```

**Solution**: Ensure your data is sampled at 500 Hz. The service is initialized with:

```python
service = AimClubECGService(sampling_rate=500)
```

## Example Workflow

Here's a complete example combining both NeuroKit2 and AimClub:

```python
from app.services.ecg_processor import ECGProcessor
from app.services.aimclub_ecg_service import AimClubECGService

# 1. Load and get signal quality (NeuroKit2)
nk_processor = ECGProcessor(sampling_rate=500)
nk_results = nk_processor.analyze_file('Device_1_Volts.txt', duration=10.0)

print(f"Signal Quality: {nk_results['quality']['overall_grade']}")
print(f"Heart Rate: {nk_results['statistics'].heart_rate_mean:.1f} bpm")

# 2. If quality is good, run clinical analysis (AimClub)
if nk_results['quality']['overall_grade'] in ['Good', 'Excellent']:
    aimclub_service = AimClubECGService(sampling_rate=500)
    clinical_results = aimclub_service.analyze_ecg_complete(
        'Device_1_Volts.txt',
        duration=10.0,
        include_nn_analysis=True
    )

    print(f"ST-Elevation: {clinical_results['st_elevation_classic']['st_elevation_detected']}")
    print(f"Diagnosis: {clinical_results['diagnosis_risk_markers']['diagnosis']}")
```

## Next Steps

1. **Test the integration**: Run `python test_aimclub_integration.py`
2. **Try the API**: Use the `/api/analyze-aimclub` endpoint
3. **Explore the notebook**: Check `test_aimclub_ecg.ipynb` for interactive examples
4. **Combine analyses**: Use both NeuroKit2 and AimClub for comprehensive ECG evaluation

## References

- [AimClub ECG GitHub](https://github.com/aimclub/ECG)
- [AimClub ECG Documentation](https://aimclub.github.io/ECG/)
- Your tutorial notebook: `intro_to_ECG.ipynb`
- Your test notebook: `test_aimclub_ecg.ipynb`
