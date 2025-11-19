````markdown
# ECG Processing Service

Full-stack application for analyzing ADS1298 ECG data using NeuroKit2. Combines a FastAPI backend with a web-based frontend for easy file upload and heart rate analysis visualization.

## 🌟 Features

### Backend

- Parse ADS1298 .txt exports with metadata extraction
- Comprehensive ECG analysis with R-peak detection
- Heart rate statistics (mean, std, min, max)
- Optional signal data export (raw, cleaned, heart rate)
- RESTful API with automatic OpenAPI documentation
- Structured logging and health checks

### Frontend

- Simple web interface for ECG file upload
- Real-time analysis progress indication
- Beautiful visualization of heart rate statistics
- Optional signal charts (raw ECG, cleaned signal, heart rate over time)
- Responsive design for mobile and desktop
- No build tools required - pure HTML/CSS/JavaScript

## 🚀 Quick Start

### Option 1: Run Full Stack Locally

```bash
# Clone repository
git clone https://github.com/kianyew1/ECG-FastAPI-Backend.git
cd ECG-FastAPI-Backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server (serves both API and frontend)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open browser
# Frontend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Deploy to Railway.app

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete Railway deployment instructions.

**Quick deploy:**

1. Push code to GitHub
2. Visit [railway.app/new](https://railway.app/new)
3. Connect repository and deploy
4. Railway auto-detects Dockerfile and deploys full stack

## 📋 API Endpoints

### Health Check

```bash
GET /api/health
```

### Analyze ECG File

```bash
POST /api/analyze
Content-Type: multipart/form-data

Parameters:
- file: ECG data file (.txt) [required]
- duration: Duration to process in seconds [optional]
- channels: Comma-separated channel names (e.g., "CH2,CH3,CH4") [optional]
- include_signals: Include full signal data (true/false) [optional, default: false]
- sampling_rate: Sampling rate in Hz [optional, default: 500]
```

Example with curl:

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -F "file=@Device_0_Volts.txt" \
  -F "duration=20" \
  -F "channels=CH2,CH3,CH4" \
  -F "include_signals=false"
```

## 📊 Response Format

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

## 🎨 Frontend Usage

1. **Open the web interface**

   - Local: `http://localhost:8000`
   - Production: `https://your-app.up.railway.app`

2. **Upload ECG file**

   - Click "Choose ECG file (.txt)"
   - Select your ADS1298 data file
   - Configure optional parameters:
     - Duration (seconds to analyze)
     - Channels (e.g., CH2,CH3,CH4)
     - Sampling rate (Hz)
     - Include signals (enable to see charts)

3. **View results**

   - Recording metadata (date, duration, channels)
   - Heart rate statistics (mean, std dev, min, max)
   - R-peaks count and sampling information
   - Signal charts (if enabled)

4. **Analyze another file**
   - Click "Analyze Another File" button to reset

## ⚙️ Configuration

Environment variables (all optional with defaults):

| Variable                | Default                     | Description                    |
| ----------------------- | --------------------------- | ------------------------------ |
| `PORT`                  | `8000`                      | Server port (Railway auto-set) |
| `API_HOST`              | `0.0.0.0`                   | API host binding               |
| `DEBUG`                 | `false`                     | Enable debug logging           |
| `CORS_ORIGINS`          | `["*.up.railway.app", ...]` | Allowed CORS origins           |
| `MAX_UPLOAD_SIZE_MB`    | `50`                        | Maximum file upload size       |
| `TEMP_DIR`              | `/tmp/ecg_uploads`          | Temporary file storage         |
| `DEFAULT_SAMPLING_RATE` | `500`                       | Default sampling rate (Hz)     |
| `MAX_DURATION_SECONDS`  | `300`                       | Maximum processing duration    |

## 🏗️ Project Structure

```
python-ecg-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application + static file serving
│   ├── config.py            # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── ecg_models.py    # Pydantic models
│   └── services/
│       ├── __init__.py
│       └── ecg_processor.py # ECG processing logic (NeuroKit2)
├── frontend/
│   ├── index.html           # Web interface
│   ├── styles.css           # Styling
│   └── app.js               # Frontend logic
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container configuration
├── railway.json             # Railway deployment config
├── DEPLOYMENT.md            # Detailed deployment guide
└── README.md
```

## 🧪 Development

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

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t ecg-processing-service .

# Run the container
docker run -d \
  -p 8000:8000 \
  --name ecg-service \
  ecg-processing-service

# View logs
docker logs -f ecg-service

# Access application
# Frontend: http://localhost:8000
# API: http://localhost:8000/api/*
```

## 🧪 Testing

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Test API endpoint
python test_api.py
```

## 🚀 Deployment

### Railway.app (Recommended)

Complete deployment guide: [DEPLOYMENT.md](./DEPLOYMENT.md)

**Quick steps:**

1. Push to GitHub
2. Connect repo on [railway.app/new](https://railway.app/new)
3. Click "Deploy Now"
4. Generate public domain
5. Access your app at `https://your-app.up.railway.app`

### Other Platforms

**Docker-based platforms** (Render, Fly.io, etc.):

- Use included `Dockerfile`
- Set `PORT` environment variable
- Deploy from GitHub or Docker registry

**Cloud providers** (GCP Cloud Run, AWS ECS):

- Build and push Docker image
- Configure environment variables
- Set health check to `/api/health`

## 📖 Documentation

- **API Documentation**: Visit `/docs` for interactive Swagger UI
- **Deployment Guide**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Quick Start**: See [QUICKSTART.md](./QUICKSTART.md)

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.11
- **ECG Processing**: NeuroKit2, NumPy, Pandas, SciPy
- **Frontend**: Vanilla JavaScript, Chart.js
- **Deployment**: Docker, Railway.app
- **API Docs**: OpenAPI/Swagger (auto-generated)

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a pull request.

## 📧 Support

For issues and questions:

- Open a GitHub issue
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for troubleshooting
````

`````
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
`````
