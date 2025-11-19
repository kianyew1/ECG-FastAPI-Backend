# ECG Analysis Frontend

Simple, responsive web interface for uploading and analyzing ECG data files.

## Features

- 📤 **File Upload**: Drag-and-drop or click to select ADS1298 `.txt` files
- ⚙️ **Configurable Parameters**: Adjust duration, channels, and sampling rate
- 📊 **Statistics Display**: View heart rate metrics in clear, organized cards
- 📈 **Signal Visualization**: Optional charts for raw ECG, cleaned signals, and heart rate
- 📱 **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- 🎨 **Modern UI**: Clean, professional interface with smooth animations
- 🚀 **Zero Build Tools**: Pure HTML/CSS/JS - no webpack, npm, or build process

## Usage

### Access the Frontend

**Local Development:**

```
http://localhost:8000
```

**Production (Railway):**

```
https://your-app-name.up.railway.app
```

### Upload and Analyze

1. **Select File**

   - Click "Choose ECG file (.txt)" or drag file onto the upload area
   - Only `.txt` files are accepted
   - Maximum file size: 50MB (configurable)

2. **Configure Parameters** (all optional)

   - **Duration**: Limit analysis to first N seconds (leave blank for full file)
   - **Channels**: Comma-separated channel list (default: CH2,CH3,CH4)
   - **Sampling Rate**: Hz (default: 500)
   - **Include Signals**: Check to see time-series charts (slower, larger response)

3. **Analyze**

   - Click "Analyze ECG"
   - Wait for processing (typically 1-5 seconds)
   - View results on the same page

4. **View Results**

   - **Metadata**: Recording info, duration, channels used
   - **Statistics**: Mean HR, std deviation, min/max HR, R-peaks count
   - **Charts** (if enabled): Raw signal, cleaned signal, heart rate over time, R-peaks

5. **Analyze Another**
   - Click "← Analyze Another File" to reset and upload new file

## File Format

The frontend accepts ADS1298 ECG data files in `.txt` format with the following structure:

```
Record #: 123
Date: 11/19/2025 14:30:00
Notes: Patient at rest
Gain: 24x

CH1    CH2    CH3    CH4    CH5    CH6    CH7    CH8
0.123  0.456  0.789  ...
0.124  0.457  0.790  ...
...
```

## API Integration

The frontend communicates with the backend via the `/api/analyze` endpoint:

### Request

```javascript
const formData = new FormData();
formData.append("file", fileObject);
formData.append("duration", "20"); // optional
formData.append("channels", "CH2,CH3,CH4"); // optional
formData.append("include_signals", "true"); // optional
formData.append("sampling_rate", "500"); // optional

fetch("/api/analyze", {
  method: "POST",
  body: formData,
});
```

### Response

```json
{
  "metadata": {
    "record_number": "123",
    "datetime": "11/19/2025 14:30:00",
    "duration_seconds": 20.0,
    "sample_count": 10000,
    "processed_channel": "CH2",
    "channels_available": ["CH2", "CH3", "CH4"]
  },
  "statistics": {
    "heart_rate_mean": 72.5,
    "heart_rate_std": 3.2,
    "heart_rate_min": 68.0,
    "heart_rate_max": 78.0,
    "r_peaks_count": 24,
    "sampling_rate": 500
  },
  "raw_signal": { "time": [...], "values": [...] },
  "cleaned_signal": { "time": [...], "values": [...] },
  "heart_rate_signal": { "time": [...], "values": [...] },
  "r_peak_times": [...],
  "r_peak_amplitudes": [...]
}
```

## Customization

### Styling

Edit `styles.css` to customize appearance:

```css
:root {
  --primary-color: #2563eb; /* Blue - change to your brand color */
  --success-color: #10b981; /* Green */
  --error-color: #ef4444; /* Red */
  /* ... more variables */
}
```

### Chart Configuration

Edit `app.js` to customize Chart.js options:

```javascript
const chartConfig = {
  responsive: true,
  aspectRatio: 3, // Change chart proportions
  // ... more options
};
```

### Downsampling

Large datasets are automatically downsampled for performance:

```javascript
const maxPoints = 2000; // Increase for more detail, decrease for better performance
```

## Browser Compatibility

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

**Required features:**

- FormData API
- Fetch API
- ES6+ JavaScript
- CSS Grid and Flexbox

## Performance

### Tips for Large Files

1. **Disable signal visualization** for files > 10,000 samples
2. **Limit duration** to analyze only needed portion
3. **Use single channel** instead of multiple channels
4. **Close other browser tabs** to free up memory

### Expected Performance

| File Size | Sample Count | With Signals | Time   |
| --------- | ------------ | ------------ | ------ |
| 1 MB      | ~5,000       | No           | < 1s   |
| 1 MB      | ~5,000       | Yes          | 2-3s   |
| 10 MB     | ~50,000      | No           | 2-3s   |
| 10 MB     | ~50,000      | Yes          | 5-10s  |
| 50 MB     | ~250,000     | No           | 10-15s |
| 50 MB     | ~250,000     | Yes          | 30-60s |

## Troubleshooting

### File Upload Fails

**Problem**: "Invalid file type" error  
**Solution**: Ensure file has `.txt` extension

**Problem**: "File too large" error  
**Solution**: File exceeds 50MB limit. Try:

- Limiting duration parameter
- Splitting file into smaller recordings
- Ask admin to increase `MAX_UPLOAD_SIZE_MB`

### No Results Display

**Problem**: Blank screen after upload  
**Solution**:

- Check browser console for errors (F12)
- Verify backend is running (`/api/health` should return 200)
- Try hard refresh (Ctrl+Shift+R / Cmd+Shift+R)

### Charts Not Showing

**Problem**: Statistics show but no charts  
**Solution**:

- Ensure "Include signal data & charts" is checked
- Verify Chart.js CDN is accessible
- Check browser console for errors

### Slow Performance

**Problem**: Analysis takes very long  
**Solution**:

- Disable "Include signals" checkbox
- Reduce duration parameter
- Use faster internet connection (affects upload time)
- Check server resources (Railway metrics)

## Development

### Local Testing

```bash
# Start backend (from project root)
uvicorn app.main:app --reload --port 8000

# Access frontend
open http://localhost:8000
```

### File Structure

```
frontend/
├── index.html    # Main HTML structure
├── styles.css    # All styling and responsive design
└── app.js        # JavaScript logic and API calls
```

### Adding Features

**Example: Add new statistic display**

1. Update `index.html`:

```html
<div class="stat-box">
  <div class="stat-label">New Metric</div>
  <div id="newMetric" class="stat-value">-</div>
  <div class="stat-unit">units</div>
</div>
```

2. Update `app.js`:

```javascript
function displayResults(data, includeSignals) {
  // ... existing code ...
  document.getElementById("newMetric").textContent =
    data.statistics.new_metric.toFixed(1);
}
```

## Dependencies

### External Libraries

- **Chart.js v4.4.0**: Signal visualization (loaded from CDN)
  - Source: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
  - License: MIT
  - Size: ~200KB

### No Build Tools Required

All other code is vanilla JavaScript, HTML, and CSS. No npm, webpack, babel, or other build tools needed.

## Security Considerations

- ✅ Files processed server-side only (not stored in browser)
- ✅ HTTPS enforced in production (Railway provides SSL)
- ✅ File type validation on client and server
- ✅ Size limits prevent abuse
- ✅ No sensitive data stored in localStorage
- ✅ CORS configured for security

## Accessibility

- Semantic HTML structure
- Proper label associations
- Keyboard navigation support
- Screen reader friendly
- High contrast text
- Responsive touch targets (44x44px minimum)

## License

MIT - Same as parent project

## Support

For frontend-specific issues:

1. Check browser console (F12) for errors
2. Verify API is accessible: `/api/health`
3. Review [DEPLOYMENT.md](../DEPLOYMENT.md) troubleshooting section
4. Open GitHub issue with:
   - Browser and version
   - Console errors
   - Steps to reproduce
