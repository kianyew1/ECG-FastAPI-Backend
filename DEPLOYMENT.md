# Railway.app Deployment Guide

This guide covers deploying the ECG Analysis Service (backend + frontend) to Railway.app as a single containerized application.

## 🏗️ Architecture

The application is deployed as a unified service where:

- FastAPI serves the REST API at `/api/*` endpoints
- Static frontend files are served from the root `/` path
- Single Docker container handles both frontend and backend
- No CORS issues since both are served from the same origin

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Code must be pushed to GitHub
3. **Railway CLI** (optional): Install via `npm i -g @railway/cli`

## 🚀 Deployment Steps

### Option 1: Deploy via Railway Dashboard (Recommended)

1. **Connect Repository**

   - Go to [railway.app/new](https://railway.app/new)
   - Click "Deploy from GitHub repo"
   - Authorize Railway to access your GitHub account
   - Select the `ECG-FastAPI-Backend` repository

2. **Configure Service**

   - Railway will auto-detect the Dockerfile
   - Click "Deploy Now" to start the build
   - Wait for the initial deployment (2-3 minutes)

3. **Configure Environment Variables** (Optional)

   - Click on your service
   - Go to "Variables" tab
   - Add any custom configuration:
     ```
     DEBUG=false
     MAX_UPLOAD_SIZE_MB=50
     MAX_DURATION_SECONDS=300
     DEFAULT_SAMPLING_RATE=500
     ```

4. **Generate Public URL**

   - Go to "Settings" tab
   - Click "Generate Domain" under "Networking"
   - Your app will be available at: `https://your-app-name.up.railway.app`

5. **Verify Deployment**
   - Visit `https://your-app-name.up.railway.app` (frontend)
   - Visit `https://your-app-name.up.railway.app/api/health` (API health check)
   - Visit `https://your-app-name.up.railway.app/docs` (API documentation)

### Option 2: Deploy via Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project (in your repo directory)
railway init

# Link to existing project or create new
railway link

# Deploy
railway up

# Generate domain
railway domain
```

## 🔧 Configuration

### Environment Variables

The application supports the following environment variables (all optional with sensible defaults):

| Variable                | Default                    | Description                                   |
| ----------------------- | -------------------------- | --------------------------------------------- |
| `PORT`                  | `8000`                     | Server port (Railway sets this automatically) |
| `API_HOST`              | `0.0.0.0`                  | Server bind address                           |
| `DEBUG`                 | `false`                    | Enable debug mode                             |
| `APP_NAME`              | `"ECG Processing Service"` | Application name                              |
| `APP_VERSION`           | `"1.0.0"`                  | Application version                           |
| `MAX_UPLOAD_SIZE_MB`    | `50`                       | Maximum file upload size                      |
| `MAX_DURATION_SECONDS`  | `300`                      | Maximum ECG duration to process               |
| `DEFAULT_SAMPLING_RATE` | `500`                      | Default sampling rate (Hz)                    |
| `DEFAULT_CHANNELS`      | `["CH2","CH3","CH4"]`      | Default channels to analyze                   |
| `TEMP_DIR`              | `"/tmp/ecg_uploads"`       | Temporary file storage directory              |

### CORS Configuration

CORS is pre-configured to allow Railway domains:

- `https://*.up.railway.app` (Railway production)
- `http://localhost:3000` (local development)
- `http://localhost:3001` (local development)

To add custom domains, set `CORS_ORIGINS` environment variable:

```bash
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
```

## 🏥 Health Checks

Railway automatically monitors the health check endpoint:

- **Path**: `/api/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

Successful response:

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## 📊 Monitoring & Logs

### View Logs

```bash
# Via CLI
railway logs

# Or in Dashboard
# Click service → "Deployments" tab → Select deployment → View logs
```

### Metrics

Railway provides built-in metrics:

- CPU usage
- Memory usage
- Network traffic
- Request count
- Response times

Access via: Dashboard → Service → "Metrics" tab

## 🔄 Updates & Redeployment

### Automatic Deployments

Railway automatically deploys when you push to the `main` branch (if configured):

```bash
git add .
git commit -m "Update ECG analysis features"
git push origin main
```

### Manual Redeployment

```bash
# Via CLI
railway up

# Or in Dashboard
# Click "Deploy" button → Select commit/branch
```

### Rollback

In the Dashboard:

1. Go to "Deployments" tab
2. Find previous successful deployment
3. Click "⋯" → "Redeploy"

## 🧪 Testing Your Deployment

### 1. Test Frontend

Visit your Railway URL in a browser:

```
https://your-app-name.up.railway.app
```

You should see the ECG Analysis upload interface.

### 2. Test API Endpoints

**Health Check:**

```bash
curl https://your-app-name.up.railway.app/api/health
```

**API Documentation:**

```
https://your-app-name.up.railway.app/docs
```

**Upload Test File:**

```bash
curl -X POST "https://your-app-name.up.railway.app/api/analyze" \
  -F "file=@path/to/your/ecg_data.txt" \
  -F "duration=10" \
  -F "channels=CH2,CH3,CH4" \
  -F "include_signals=false" \
  -F "sampling_rate=500"
```

### 3. Test File Upload via Frontend

1. Open your Railway URL
2. Click "Choose ECG file (.txt)"
3. Select a test ECG file
4. Configure optional parameters
5. Click "Analyze ECG"
6. Verify results display correctly

## 🐛 Troubleshooting

### Build Fails

- **Check Dockerfile**: Ensure all files are copied correctly
- **Check dependencies**: Verify `requirements.txt` is complete
- **View build logs**: Dashboard → Deployments → Build logs

### App Crashes

- **Check logs**: `railway logs` or Dashboard logs
- **Memory issues**: Upgrade to Railway Pro plan for more resources
- **Environment variables**: Verify all required variables are set

### Frontend Not Loading

- **Check build**: Ensure `frontend/` directory exists and is copied in Dockerfile
- **Check route order**: API routes must be defined before static file mounting
- **Clear cache**: Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)

### API Returns 404

- **Check URL**: API endpoints are at `/api/*` not root
- **Check deployment**: Verify service is running in Dashboard
- **Check health**: Visit `/api/health` endpoint

### CORS Errors

- **Local development**: Add your local URL to `CORS_ORIGINS`
- **Custom domain**: Update `CORS_ORIGINS` environment variable
- **Railway domain**: Pre-configured with `*.up.railway.app` wildcard

### File Upload Fails

- **Size limit**: Check file is under `MAX_UPLOAD_SIZE_MB` (default 50MB)
- **File format**: Only `.txt` files are accepted
- **Duration limit**: Ensure duration doesn't exceed `MAX_DURATION_SECONDS`
- **Memory**: Large files may require more memory (upgrade plan)

## 💰 Pricing Considerations

Railway pricing (as of 2024):

- **Hobby Plan**: $5/month for 500 hours of usage
- **Pro Plan**: $20/month for unlimited usage + more resources

Tips to optimize usage:

- Set `DEBUG=false` in production (reduces logging overhead)
- Configure appropriate `MAX_UPLOAD_SIZE_MB` limit
- Consider sleep/wake patterns if traffic is low
- Monitor metrics to right-size your deployment

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit `.env` files to git
2. **File Validation**: Application validates file types and sizes
3. **CORS**: Restrict `CORS_ORIGINS` to your actual domains
4. **HTTPS**: Railway provides automatic SSL certificates
5. **Temp Files**: Automatically cleaned up after processing
6. **Error Handling**: Sensitive details not exposed in error messages

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NeuroKit2 Documentation](https://neuropsychology.github.io/NeuroKit/)
- [Project Repository](https://github.com/kianyew1/ECG-FastAPI-Backend)

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Railway logs: `railway logs`
3. Check Railway status: [status.railway.app](https://status.railway.app)
4. Open an issue on GitHub
5. Contact Railway support (Pro plan)

---

**Version**: 1.0.0  
**Last Updated**: November 2025
