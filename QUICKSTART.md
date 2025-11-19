# Python ECG Backend - Quick Start

## Installation Complete! ✅

Your Jupyter notebook has been successfully converted into a deployable FastAPI backend.

## What Was Created

### Core Application Files

- **`app/main.py`** - FastAPI application with `/analyze` and `/health` endpoints
- **`app/config.py`** - Configuration management with environment variables
- **`app/models/ecg_models.py`** - Pydantic models for request/response validation
- **`app/services/ecg_processor.py`** - ECG processing logic from notebook

### Deployment Files

- **`Dockerfile`** - Container image for deployment
- **`.dockerignore`** - Files to exclude from Docker builds
- **`start.sh`** - Local startup script
- **`.env.example`** - Configuration template

### Testing

- **`test_api.py`** - API test script with examples

## Quick Start

### 1. Start the Server

```bash
# Option 1: Using the startup script
./start.sh

# Option 2: Direct uvicorn command
cd /Users/kianyew/Desktop/projects/capstone/python-ecg-backend
source .venv/bin/activate
export PYTHONPATH=$(pwd)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access the API

- **API Docs (Swagger)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Analyze ECG file
curl -X POST "http://localhost:8000/analyze" \
  -F "file=@../ecg-webapp/public/Readings 2025-11-12 Zorye post run/Device_0_Volts.txt" \
  -F "duration=20" \
  -F "channels=CH2,CH3,CH4" \
  -F "include_signals=false"

# Using the test script
python test_api.py
```

## API Endpoints

### POST /analyze

Upload and analyze ECG files.

**Parameters:**

- `file` - ECG data file (.txt) [required]
- `duration` - Duration to process (seconds) [optional]
- `channels` - Comma-separated channels (e.g., "CH2,CH3,CH4") [optional]
- `include_signals` - Include full signal data (true/false) [optional]
- `sampling_rate` - Sampling rate in Hz (default: 500) [optional]

**Response:**

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
  }
}
```

### GET /health

Health check endpoint.

## Docker Deployment

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

# Stop and remove
docker stop ecg-service
docker rm ecg-service
```

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` to configure:

- API host and port
- CORS origins for your frontend
- File upload limits
- Processing defaults

## Integration with Frontend

Update your Next.js frontend to call this API:

```typescript
// Example frontend integration
const analyzeECG = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("duration", "20");
  formData.append("channels", "CH2,CH3,CH4");
  formData.append("include_signals", "false");

  const response = await fetch("http://localhost:8000/analyze", {
    method: "POST",
    body: formData,
  });

  return await response.json();
};
```

## Next Steps

1. **Test with your ECG files** - Run `python test_api.py`
2. **Integrate with frontend** - Update CORS_ORIGINS in `.env`
3. **Deploy to cloud** - Use Docker image with Cloud Run, ECS, or Railway
4. **Add authentication** - Implement API keys or OAuth if needed
5. **Monitor performance** - Add logging and metrics

## Troubleshooting

**Port already in use:**

```bash
lsof -ti:8000 | xargs kill -9
```

**Module not found:**

```bash
export PYTHONPATH=$(pwd)
```

**Dependencies missing:**

```bash
pip install -r requirements.txt
```

## Documentation

- Full API docs: http://localhost:8000/docs (when running)
- See `README.md` for complete documentation
- Check `app/models/ecg_models.py` for data schemas
