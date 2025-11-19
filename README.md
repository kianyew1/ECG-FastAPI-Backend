````markdown
# ECG Processing Service

FastAPI microservice for analyzing ADS1298 ECG data using NeuroKit2.

## Features

- Parse ADS1298 .txt exports with metadata extraction
- Comprehensive ECG analysis with R, P, Q, S, T wave detection
- Heart rate statistics (mean, std, min, max)
- Optional signal data export (raw, cleaned, heart rate)
- CORS support for web frontends
- Structured logging
- Health check endpoint

## Installation

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env with your settings

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build the image
docker build -t ecg-processing-service .

# Run the container
docker run -d \
  -p 8000:8000 \
  -e CORS_ORIGINS=http://localhost:3000 \
  --name ecg-service \
  ecg-processing-service

# View logs
docker logs -f ecg-service
```

## API Endpoints

### Health Check

```bash
GET /health
```

### Analyze ECG File

```bash
POST /analyze
Content-Type: multipart/form-data

Parameters:
- file: ECG data file (.txt) [required]
- duration: Duration to process in seconds [optional]
- channels: Comma-separated channel names (e.g., "CH2,CH3,CH4") [optional]
- include_signals: Include full signal data (true/false) [optional]
- sampling_rate: Sampling rate in Hz (default: 500) [optional]
```

Example with curl:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@Device_0_Volts.txt" \
  -F "duration=20" \
  -F "channels=CH2,CH3,CH4" \
  -F "include_signals=false"
```

## Response Format

```json
{
  "metadata": {
    "record_number": "123",
    "datetime": "11/12/2025 14:30:00",
    "notes": "Post-exercise recording",
    "gain": "Gain: 24x",
    "duration_seconds": 20.0,
    "sample_count": 10000,
    "channels_available": ["CH2", "CH3", "CH4"],
    "processed_channel": "CH2"
  },
  "statistics": {
    "heart_rate_mean": 72.5,
    "heart_rate_std": 3.2,
    "heart_rate_min": 68.0,
    "heart_rate_max": 78.0,
    "r_peaks_count": 24,
    "sampling_rate": 500
  },
  "raw_signal": null,
  "cleaned_signal": null,
  "heart_rate_signal": null,
  "r_peak_times": null,
  "r_peak_amplitudes": null
}
```

## Configuration

Environment variables (see `.env.example`):

| Variable                | Default                 | Description                 |
| ----------------------- | ----------------------- | --------------------------- |
| `API_HOST`              | `0.0.0.0`               | API host binding            |
| `API_PORT`              | `8000`                  | API port                    |
| `DEBUG`                 | `false`                 | Enable debug logging        |
| `CORS_ORIGINS`          | `http://localhost:3000` | Allowed CORS origins        |
| `MAX_UPLOAD_SIZE_MB`    | `50`                    | Maximum file upload size    |
| `TEMP_DIR`              | `/tmp/ecg_uploads`      | Temporary file storage      |
| `DEFAULT_SAMPLING_RATE` | `500`                   | Default sampling rate (Hz)  |
| `MAX_DURATION_SECONDS`  | `300`                   | Maximum processing duration |

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with auto-reload
uvicorn app.main:app --reload

# API documentation (auto-generated)
# Visit: http://localhost:8000/docs
```

## Project Structure

```
python-ecg-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── ecg_models.py    # Pydantic models
│   └── services/
│       ├── __init__.py
│       └── ecg_processor.py # ECG processing logic
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Test specific endpoint
pytest tests/test_api.py::test_analyze_endpoint
```

## Deployment Options

### Cloud Run (GCP)

```bash
gcloud run deploy ecg-service \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### AWS ECS/Fargate

1. Push image to ECR
2. Create task definition
3. Deploy service with ALB

### Railway/Render

1. Connect GitHub repository
2. Set environment variables
3. Deploy automatically on push

## License

MIT
````
