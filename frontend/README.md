# ECG Analysis Frontend

Simple, responsive web interface for uploading and analyzing ECG data files.

## Features

- 📤 **File Upload**: Drag-and-drop or click to select ADS1298 `.txt` files
- 🔍 **Channel Preview**: Real-time preview of selected channel with quality assessment
- 📊 **Signal Quality Analysis**: Advanced quality metrics (mSQI, kSQI) with visual indicators
- ⚙️ **Configurable Parameters**: Adjust timeframe, channels, and sampling rate
- 🎯 **Timeframe Selection**: Interactive sliders to select specific signal segments for analysis
- 📈 **Multi-Signal Visualization**: Raw ECG, cleaned signals, heart rate, and R-peaks detection
- 📊 **Statistics Display**: View heart rate metrics in clear, organized cards
- ✅ **Quality Assessment**: Window-by-window quality analysis with best segment identification
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

2. **Load File Metadata**

   - Click "Load ECG File" to upload and preview file metadata
   - View available channels and total duration
   - No signal processing yet - just metadata extraction

3. **Configure Analysis Parameters**

   - **Sampling Rate**: Hz (default: 500)
   - **Channel Selection**: Choose which ECG channel to analyze from dropdown
   - **Include Signals**: Check to include time-series charts in results

4. **Preview Channel & Quality Assessment**

   - Select a channel to see real-time preview with quality assessment
   - View cleaned signal with annotations showing selected timeframe
   - Quality card displays:
     - **Quality Chart**: Signal visualization with best/poor segments highlighted
     - **Quality Summary**: Overall status, quality rate, good windows count
     - **Best Segment**: Time range of highest quality data
     - **Detailed Analysis**: Window-by-window metrics (mSQI, kSQI, HR, SDNN, status)

5. **Select Timeframe**

   - Use interactive sliders to select start and end time
   - Green box shows selected segment on preview chart
   - View selected duration and estimated sample count
   - Default: Full signal duration

6. **Analyze Selected Segment**

   - Click "Analyze Selected Timeframe"
   - Wait for processing (typically 1-5 seconds)
   - View comprehensive results

7. **View Analysis Results**

   - **Metadata**: Recording info, duration, channels used, gain settings
   - **Statistics**: Mean HR, std deviation, min/max HR, R-peaks count
   - **Charts** (if enabled): Raw signal, cleaned signal, heart rate over time, R-peaks overlay

8. **Analyze Another**
   - Click "← New Analysis" to reset and upload new file

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
formData.append("channels", "CH2"); // Single channel to analyze
formData.append("duration", "20"); // optional - duration in seconds
formData.append("include_signals", "true"); // optional - include chart data
formData.append("sampling_rate", "500"); // optional - expected sampling rate

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
    "channels_available": ["CH2", "CH3", "CH4"],
    "notes": "Patient at rest",
    "gain": "24x"
  },
  "statistics": {
    "heart_rate_mean": 72.5,
    "heart_rate_std": 3.2,
    "heart_rate_min": 68.0,
    "heart_rate_max": 78.0,
    "r_peaks_count": 24,
    "sampling_rate": 500
  },
  "quality_assessment": {
    "summary": {
      "status": "GOOD",
      "total_windows": 11,
      "good_windows": 8,
      "adequate_windows": 2,
      "rejected_windows": 1,
      "good_percentage": 72.7
    },
    "windows": [
      {
        "window": 1,
        "start_time": 0.0,
        "end_time": 10.0,
        "mSQI": 0.823,
        "kSQI": 2.95,
        "heart_rate": 139.3,
        "sdnn": 7.55,
        "status": "REJECTED (External Artifact)"
      }
      // ... more windows
    ],
    "best_segment_times": [6.0, 16.0],
    "bad_segment_times": [[0.0, 11.0]]
  },
  "raw_signal": { "time": [...], "values": [...] },
  "cleaned_signal": { "time": [...], "values": [...] },
  "heart_rate_signal": { "time": [...], "values": [...] },
  "r_peak_times": [...],
  "r_peak_amplitudes": [...]
}
```

## Signal Quality Assessment

The frontend includes comprehensive ECG signal quality analysis to help identify the best segments for reliable heart rate analysis.

### Quality Metrics

**mSQI (Modified Signal Quality Index)**

- Range: 0.0 to 1.0
- Measures signal-to-noise ratio and morphological consistency
- Higher values indicate cleaner signals
- Threshold: > 0.7 for "GOOD" quality

**kSQI (Kurtosis-based Signal Quality Index)**

- Measures statistical properties of the signal
- Detects artifacts and abnormal waveforms
- Combined with mSQI for comprehensive assessment

### Quality Status Categories

- **GOOD**: High-quality signal suitable for analysis (green)
- **ADEQUATE**: Acceptable quality with minor artifacts (yellow)
- **REJECTED**: Poor quality due to artifacts or noise (red)

### Quality Visualization

**Quality Chart:**

- Cleaned ECG signal with color-coded quality annotations
- Green box: Best quality segment identified by the algorithm
- Red-shaded areas: Poor quality segments to avoid
- Interactive zoom and pan

**Quality Summary Card:**

- Overall quality status
- Percentage of good-quality windows
- Count of good/adequate/rejected windows
- Best segment time range
- Best window mSQI and kSQI values

**Detailed Window Analysis Table:**

- Expandable table with per-window metrics
- 10-second windows (configurable on backend)
- Each window shows:
  - Time range
  - mSQI and kSQI scores
  - Heart rate and SDNN
  - Quality status with visual badge

### Using Quality Assessment

1. **Preview Mode**: Quality assessment automatically runs when you select a channel
2. **Review Metrics**: Check the quality summary to assess overall signal quality
3. **Select Best Segment**: Use the identified best segment time range for analysis
4. **Adjust Timeframe**: Use sliders to select high-quality portions
5. **Avoid Artifacts**: Exclude red-shaded poor quality segments

### Quality-Aware Analysis Tips

- Focus analysis on segments marked as "GOOD" (green badges)
- Avoid segments with external artifacts or baseline wander
- Use the best segment recommendation for most reliable results
- If overall quality is poor, consider re-recording or trying different channels

## Customization

### Styling

Edit `styles.css` to customize appearance:

```css
:root {
  --primary-color: #2563eb; /* Blue - change to your brand color */
  --success-color: #10b981; /* Green */
  --error-color: #ef4444; /* Red */
  --text-primary: #1f2937; /* Dark gray */
  --text-secondary: #6b7280; /* Medium gray */
  --bg-primary: #ffffff; /* White */
  --bg-secondary: #f9fafb; /* Light gray */
  /* ... more variables */
}
```

### Quality Assessment Thresholds

Quality metrics are calculated server-side but displayed with color coding:

```css
/* Status badge colors */
.status-good {
  background: #d1fae5;
  color: #065f46;
}
.status-adequate {
  background: #fef3c7;
  color: #92400e;
}
.status-rejected {
  background: #fee2e2;
  color: #991b1b;
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

| File Size | Sample Count | With Signals | With Quality | Time   |
| --------- | ------------ | ------------ | ------------ | ------ |
| 1 MB      | ~5,000       | No           | No           | < 1s   |
| 1 MB      | ~5,000       | Yes          | Yes          | 2-3s   |
| 10 MB     | ~50,000      | No           | No           | 2-3s   |
| 10 MB     | ~50,000      | Yes          | Yes          | 5-10s  |
| 50 MB     | ~250,000     | No           | No           | 10-15s |
| 50 MB     | ~250,000     | Yes          | Yes          | 30-60s |

**Note**: Quality assessment is automatically included with preview and adds minimal overhead.

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
- Check chartjs-plugin-annotation is loaded
- Check browser console for errors

### Quality Assessment Not Appearing

**Problem**: No quality card or quality metrics displayed  
**Solution**:

- Select a channel from the dropdown to trigger preview
- Verify backend returns `quality_assessment` in response
- Check browser console for JavaScript errors
- Ensure sufficient signal duration (minimum 10 seconds recommended)

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
├── index.html    # Main HTML structure with quality assessment UI
├── styles.css    # All styling, responsive design, and status badges
└── app.js        # JavaScript logic, API calls, and chart rendering
```

### Code Architecture

**HTML-First Approach:**

- Quality assessment structure defined in HTML
- JavaScript populates data iteratively
- Minimal inline styles, CSS classes preferred

**Key Functions:**

- `displayQualityAssessment()` - Orchestrates quality display
- `createQualityChart()` - Renders quality visualization with annotations
- `populateQualitySummary()` - Updates quality metrics cards
- `populateQualityTable()` - Builds window-by-window analysis table
- `setupTimeframeSelection()` - Configures interactive sliders
- `loadChannelPreview()` - Loads and displays channel preview with quality

### Adding Features

**Example: Add new quality metric display**

1. Update `index.html` in quality stats section:

```html
<div class="quality-stat">
  <span class="quality-label">New Metric:</span>
  <span class="quality-value">-</span>
</div>
```

2. Update `app.js` in `populateQualitySummary()`:

```javascript
const stats = [
  // ... existing stats
  {
    label: "New Metric:",
    value: qualityData.summary.new_metric.toFixed(2),
  },
];
```

**Example: Add new table column**

1. Update `index.html` table header:

```html
<th>New Column</th>
```

2. Update `app.js` in `populateQualityTable()`:

```javascript
const cells = [
  // ... existing cells
  window.new_value.toFixed(2),
];
```

## Dependencies

### External Libraries

- **Chart.js v4.4.0**: Signal visualization (loaded from CDN)

  - Source: `https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js`
  - License: MIT
  - Size: ~200KB

- **chartjs-plugin-annotation v3.0.1**: Chart annotations for quality segments and timeframe selection
  - Source: `https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.0.1/dist/chartjs-plugin-annotation.min.js`
  - License: MIT
  - Size: ~50KB

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
