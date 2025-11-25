// DOM Elements
const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const fileLabel = document.querySelector(".file-label");
const submitBtn = document.getElementById("submitBtn");
const btnText = document.getElementById("btnText");
const btnSpinner = document.getElementById("btnSpinner");
const errorMessage = document.getElementById("errorMessage");
const resultsSection = document.getElementById("resultsSection");
const chartsSection = document.getElementById("chartsSection");
const newAnalysisBtn = document.getElementById("newAnalysisBtn");
const timeframeSection = document.getElementById("timeframeSection");
const channelSelect = document.getElementById("channelSelect");
const previewCard = document.getElementById("previewCard");
const startTimeSlider = document.getElementById("startTimeSlider");
const endTimeSlider = document.getElementById("endTimeSlider");
const startTimeValue = document.getElementById("startTimeValue");
const endTimeValue = document.getElementById("endTimeValue");
const selectedDuration = document.getElementById("selectedDuration");
const selectedSamples = document.getElementById("selectedSamples");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeBtnText = document.getElementById("analyzeBtnText");
const analyzeBtnSpinner = document.getElementById("analyzeBtnSpinner");

// Chart instances
let charts = {};

// Global state
let previewData = null;
let currentFile = null;
let maxDuration = 0;
let samplingRate = 500;

// Channel selection handler
channelSelect.addEventListener("change", (e) => {
  if (e.target.value) {
    loadChannelPreview(e.target.value);
  } else {
    previewCard.style.display = "none";
  }
});

// Sampling rate change handler
document.addEventListener("DOMContentLoaded", () => {
  const samplingRateInput = document.getElementById("samplingRate");
  if (samplingRateInput) {
    samplingRateInput.addEventListener("input", (e) => {
      samplingRate = parseInt(e.target.value) || 500;
      updateSelectedDuration();
    });
  }
});

// File input change handler
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) {
    const file = e.target.files[0];
    fileName.textContent = file.name;
    fileLabel.classList.add("has-file");
  } else {
    fileName.textContent = "Choose ECG file (.txt)";
    fileLabel.classList.remove("has-file");
  }
});

// Form submit handler - loads preview metadata only
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  // Hide any previous errors and results
  hideError();
  resultsSection.style.display = "none";
  timeframeSection.style.display = "none";

  // Get form data
  const file = fileInput.files[0];

  if (!file) {
    showError("Please select a file to upload.");
    return;
  }

  // Validate file extension
  if (!file.name.toLowerCase().endsWith(".txt")) {
    showError("Please upload a .txt file.");
    return;
  }

  // Store file
  currentFile = file;

  // Show loading state
  setLoading(true);

  try {
    // Load preview data - just metadata, no signals yet
    const formData = new FormData();
    formData.append("file", file);
    formData.append("include_signals", "false"); // Don't load signals yet, just metadata

    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`
      );
    }

    previewData = await response.json();
    console.log("Preview Data:", previewData);
    // Setup timeframe selection
    setupTimeframeSelection();
  } catch (error) {
    console.error("Error:", error);
    showError(`Failed to load file: ${error.message}`);
  } finally {
    setLoading(false);
  }
});

// Setup timeframe selection UI
function setupTimeframeSelection() {
  // Populate channel selector with all available channels
  channelSelect.innerHTML = '<option value="">Select a channel...</option>';
  previewData.metadata.channels_available.forEach((channel) => {
    const option = document.createElement("option");
    option.value = channel;
    option.textContent = channel;
    channelSelect.appendChild(option);
  });

  // Select first channel by default
  if (previewData.metadata.channels_available.length > 0) {
    channelSelect.value = previewData.metadata.channels_available[0];
  }

  // Set up duration
  maxDuration = previewData.metadata.duration_seconds;
  startTimeSlider.max = maxDuration;
  endTimeSlider.max = maxDuration;
  endTimeSlider.value = maxDuration;
  startTimeValue.textContent = "0.00";
  endTimeValue.textContent = maxDuration.toFixed(2);

  // Update sampling rate from input (or use default)
  samplingRate = parseInt(document.getElementById("samplingRate").value) || 500;
  updateSelectedDuration();

  // Show timeframe section
  timeframeSection.style.display = "block";
  timeframeSection.scrollIntoView({ behavior: "smooth", block: "start" });

  // Auto-load preview for the first available channel
  if (channelSelect.value) {
    loadChannelPreview(channelSelect.value);
  }
}

// Channel selection handler
channelSelect.addEventListener("change", (e) => {
  if (e.target.value) {
    loadChannelPreview(e.target.value);
  } else {
    previewCard.style.display = "none";
  }
});

// Load channel preview - fetches data for specific channel
async function loadChannelPreview(channel) {
  if (!currentFile) return;

  // Show loading state on preview card
  previewCard.style.display = "block";

  // Add a loading indicator
  const previewChart = document.getElementById("previewChart");
  const loadingDiv = document.createElement("div");
  loadingDiv.id = "previewLoading";
  loadingDiv.className = "loading-overlay";
  loadingDiv.innerHTML =
    '<div class="spinner"></div><p>Loading channel preview...</p>';
  previewChart.parentElement.insertBefore(loadingDiv, previewChart);

  try {
    // Fetch preview data for this specific channel
    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("channels", channel);
    formData.append("include_signals", "true"); // Get signals for preview
    formData.append("sampling_rate", samplingRate);

    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`
      );
    }

    const channelData = await response.json();

    // Remove loading indicator
    const loading = document.getElementById("previewLoading");
    if (loading) loading.remove();

    // Destroy existing preview chart
    if (charts.preview) {
      charts.preview.destroy();
    }

    // Create preview chart with annotations - using CLEANED signal
    const ctx = document.getElementById("previewChart");
    const maxPoints = 2000;
    const signalData = downsample(
      channelData.cleaned_signal.time,
      channelData.cleaned_signal.values,
      maxPoints
    );

    const startTime = parseFloat(startTimeSlider.value);
    const endTime = parseFloat(endTimeSlider.value);

    charts.preview = new Chart(ctx, {
      type: "line",
      data: {
        labels: signalData.x,
        datasets: [
          {
            label: `${channel} - Cleaned Signal`,
            data: signalData.y,
            borderColor: "#10b981",
            borderWidth: 1.5,
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 3,
        plugins: {
          legend: {
            display: true,
          },
          annotation: {
            annotations: {
              selectionBox: {
                type: "box",
                xMin: startTime,
                xMax: endTime,
                backgroundColor: "rgba(16, 185, 129, 0.15)",
                borderColor: "rgba(16, 185, 129, 0.5)",
                borderWidth: 2,
                label: {
                  display: true,
                  content: "Selected for Analysis",
                  position: "center",
                  color: "#059669",
                  font: {
                    weight: "bold",
                    size: 12,
                  },
                },
              },
              startLine: {
                type: "line",
                xMin: startTime,
                xMax: startTime,
                borderColor: "#10b981",
                borderWidth: 3,
                borderDash: [5, 5],
                label: {
                  display: true,
                  content: `Start: ${startTime.toFixed(2)}s`,
                  position: "start",
                  backgroundColor: "#10b981",
                  color: "white",
                  font: {
                    weight: "bold",
                    size: 11,
                  },
                  padding: 4,
                },
              },
              endLine: {
                type: "line",
                xMin: endTime,
                xMax: endTime,
                borderColor: "#ef4444",
                borderWidth: 3,
                borderDash: [5, 5],
                label: {
                  display: true,
                  content: `End: ${endTime.toFixed(2)}s`,
                  position: "end",
                  backgroundColor: "#ef4444",
                  color: "white",
                  font: {
                    weight: "bold",
                    size: 11,
                  },
                  padding: 4,
                },
              },
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: "Time (seconds)",
            },
            type: "linear",
          },
          y: {
            title: {
              display: true,
              text: "Amplitude (mV)",
            },
          },
        },
      },
    });

    // Display quality assessment if available
    if (channelData.quality_assessment) {
      displayQualityAssessment(channelData.quality_assessment, channelData.cleaned_signal);
    } else {
      // Hide quality card if no assessment data
      const qualityCard = document.getElementById("qualityCard");
      if (qualityCard) {
        qualityCard.style.display = "none";
      }
    }
  } catch (error) {
    console.error("Error loading channel preview:", error);
    showError(`Failed to load preview for ${channel}: ${error.message}`);

    // Remove loading indicator
    const loading = document.getElementById("previewLoading");
    if (loading) loading.remove();
  }
}

// Slider event handlers
startTimeSlider.addEventListener("input", (e) => {
  const startTime = parseFloat(e.target.value);
  const endTime = parseFloat(endTimeSlider.value);

  // Ensure start is before end
  if (startTime >= endTime) {
    e.target.value = Math.max(0, endTime - 0.1);
  }

  startTimeValue.textContent = parseFloat(e.target.value).toFixed(2);
  updateSelectedDuration();
  updatePreviewAnnotations();
});

endTimeSlider.addEventListener("input", (e) => {
  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(e.target.value);

  // Ensure end is after start
  if (endTime <= startTime) {
    e.target.value = Math.min(maxDuration, startTime + 0.1);
  }

  endTimeValue.textContent = parseFloat(e.target.value).toFixed(2);
  updateSelectedDuration();
  updatePreviewAnnotations();
});

// Update selected duration display
function updateSelectedDuration() {
  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);
  const duration = endTime - startTime;

  // Get current sampling rate from input if available, otherwise use stored value
  const currentSamplingRate = document.getElementById("samplingRate")
    ? parseInt(document.getElementById("samplingRate").value) || samplingRate
    : samplingRate;

  const samples = Math.round(duration * currentSamplingRate);

  selectedDuration.textContent = duration.toFixed(2);
  selectedSamples.textContent = samples.toLocaleString();
}

// Update preview chart annotations
function updatePreviewAnnotations() {
  if (!charts.preview || !charts.preview.options.plugins.annotation) return;

  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);

  const annotations = charts.preview.options.plugins.annotation.annotations;

  // Update selection box
  annotations.selectionBox.xMin = startTime;
  annotations.selectionBox.xMax = endTime;

  // Update start line
  annotations.startLine.xMin = startTime;
  annotations.startLine.xMax = startTime;
  annotations.startLine.label.content = `Start: ${startTime.toFixed(2)}s`;

  // Update end line
  annotations.endLine.xMin = endTime;
  annotations.endLine.xMax = endTime;
  annotations.endLine.label.content = `End: ${endTime.toFixed(2)}s`;

  // Update chart with animation disabled for smooth dragging
  charts.preview.update("none");
}

// Analyze button handler
analyzeBtn.addEventListener("click", async () => {
  if (!currentFile) {
    showError("No file loaded. Please start over.");
    return;
  }

  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);
  const selectedChannel = channelSelect.value;

  if (!selectedChannel) {
    showError("Please select a channel.");
    return;
  }

  // Get sampling rate from input
  samplingRate = parseInt(document.getElementById("samplingRate").value) || 500;

  // Show loading state
  setAnalyzeLoading(true);

  try {
    // Create form data with timeframe parameters
    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("channels", selectedChannel);
    formData.append("sampling_rate", samplingRate);

    // Check if user wants signals (default true, unless unchecked)
    const includeSignals = document.getElementById("includeSignals").checked;
    formData.append("include_signals", includeSignals.toString());

    // Calculate duration from timeframe
    const duration = endTime - startTime;
    formData.append("duration", duration.toString());

    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.detail || `HTTP error! status: ${response.status}`
      );
    }

    const data = await response.json();

    // Display results
    displayResults(data, includeSignals);
  } catch (error) {
    console.error("Error:", error);
    showError(`Analysis failed: ${error.message}`);
  } finally {
    setAnalyzeLoading(false);
  }
});

// New analysis button handler
newAnalysisBtn.addEventListener("click", () => {
  // Reset form
  uploadForm.reset();
  fileName.textContent = "Choose ECG file (.txt)";
  fileLabel.classList.remove("has-file");

  // Hide sections
  resultsSection.style.display = "none";
  timeframeSection.style.display = "none";
  previewCard.style.display = "none";

  // Hide quality card and destroy quality chart
  const qualityCard = document.getElementById("qualityCard");
  if (qualityCard) {
    qualityCard.style.display = "none";
  }

  // Reset state
  currentFile = null;
  previewData = null;
  channelSelect.innerHTML = '<option value="">Select a channel...</option>';

  // Destroy charts
  destroyCharts();

  // Scroll to top
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// Display results function
function displayResults(data, includeSignals) {
  // Populate metadata
  document.getElementById("recordNumber").textContent =
    data.metadata.record_number || "N/A";
  document.getElementById("datetime").textContent =
    data.metadata.datetime || "N/A";
  document.getElementById(
    "duration-value"
  ).textContent = `${data.metadata.duration_seconds.toFixed(2)} seconds`;
  document.getElementById("sampleCount").textContent =
    data.metadata.sample_count.toLocaleString();
  document.getElementById("processedChannel").textContent =
    data.metadata.processed_channel;
  document.getElementById("availableChannels").textContent =
    data.metadata.channels_available.join(", ");
  document.getElementById("notes").textContent = data.metadata.notes || "N/A";
  document.getElementById("gain").textContent = data.metadata.gain || "N/A";

  // Populate statistics
  document.getElementById("hrMean").textContent =
    data.statistics.heart_rate_mean.toFixed(1);
  document.getElementById("hrStd").textContent =
    data.statistics.heart_rate_std.toFixed(1);
  document.getElementById("hrMin").textContent =
    data.statistics.heart_rate_min.toFixed(1);
  document.getElementById("hrMax").textContent =
    data.statistics.heart_rate_max.toFixed(1);
  document.getElementById("rPeaks").textContent = data.statistics.r_peaks_count;
  document.getElementById("samplingRateResult").textContent =
    data.statistics.sampling_rate;

  // Show results section
  resultsSection.style.display = "block";

  // Handle charts if signals are included
  if (includeSignals && data.raw_signal) {
    chartsSection.style.display = "block";
    destroyCharts(); // Clear any existing charts
    createCharts(data);
  } else {
    chartsSection.style.display = "none";
  }

  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Create charts function
function createCharts(data) {
  const chartConfig = {
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 3,
    plugins: {
      legend: {
        display: false,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Time (seconds)",
        },
      },
      y: {
        title: {
          display: true,
          text: "Amplitude (mV)",
        },
      },
    },
  };

  // Downsample data for performance if needed
  const maxPoints = 2000;

  // Raw Signal Chart
  const rawData = downsample(
    data.raw_signal.time,
    data.raw_signal.values,
    maxPoints
  );
  charts.raw = new Chart(document.getElementById("rawSignalChart"), {
    type: "line",
    data: {
      labels: rawData.x,
      datasets: [
        {
          label: "Raw ECG Signal",
          data: rawData.y,
          borderColor: "#3b82f6",
          borderWidth: 1,
          pointRadius: 0,
        },
      ],
    },
    options: chartConfig,
  });

  // Cleaned Signal Chart
  const cleanedData = downsample(
    data.cleaned_signal.time,
    data.cleaned_signal.values,
    maxPoints
  );
  charts.cleaned = new Chart(document.getElementById("cleanedSignalChart"), {
    type: "line",
    data: {
      labels: cleanedData.x,
      datasets: [
        {
          label: "Cleaned ECG Signal",
          data: cleanedData.y,
          borderColor: "#10b981",
          borderWidth: 1,
          pointRadius: 0,
        },
      ],
    },
    options: chartConfig,
  });

  // Heart Rate Chart
  const hrData = downsample(
    data.heart_rate_signal.time,
    data.heart_rate_signal.values,
    maxPoints
  );
  charts.heartRate = new Chart(document.getElementById("heartRateChart"), {
    type: "line",
    data: {
      labels: hrData.x,
      datasets: [
        {
          label: "Heart Rate",
          data: hrData.y,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          borderWidth: 2,
          pointRadius: 0,
          fill: true,
        },
      ],
    },
    options: {
      ...chartConfig,
      scales: {
        x: {
          title: {
            display: true,
            text: "Time (seconds)",
          },
        },
        y: {
          title: {
            display: true,
            text: "Heart Rate (bpm)",
          },
        },
      },
    },
  });

  // R-Peaks Chart (Cleaned signal with peaks marked)
  const rPeaksData = downsample(
    data.cleaned_signal.time,
    data.cleaned_signal.values,
    maxPoints
  );
  charts.rPeaks = new Chart(document.getElementById("rPeaksChart"), {
    type: "line",
    data: {
      labels: rPeaksData.x,
      datasets: [
        {
          label: "Cleaned ECG",
          data: rPeaksData.y,
          borderColor: "#64748b",
          borderWidth: 1,
          pointRadius: 0,
        },
        {
          label: "R-Peaks",
          data: data.r_peak_times.map((time, idx) => ({
            x: time,
            y: data.r_peak_amplitudes[idx],
          })),
          borderColor: "#ef4444",
          backgroundColor: "#ef4444",
          pointRadius: 5,
          pointStyle: "circle",
          showLine: false,
        },
      ],
    },
    options: {
      ...chartConfig,
      plugins: {
        legend: {
          display: true,
        },
      },
    },
  });
}

// Downsample data for performance
function downsample(xData, yData, maxPoints) {
  if (xData.length <= maxPoints) {
    return { x: xData, y: yData };
  }

  const step = Math.ceil(xData.length / maxPoints);
  const downsampledX = [];
  const downsampledY = [];

  for (let i = 0; i < xData.length; i += step) {
    downsampledX.push(xData[i]);
    downsampledY.push(yData[i]);
  }

  return { x: downsampledX, y: downsampledY };
}

// Display quality assessment function
function displayQualityAssessment(qualityData, cleanedSignalData) {
  const qualityCard = document.getElementById("qualityCard");
  
  // Show quality card
  qualityCard.style.display = "block";
  
  // Destroy existing quality chart
  if (charts.quality) {
    charts.quality.destroy();
  }
  
  // Create quality chart canvas if it doesn't exist
  let qualityChartContainer = document.getElementById("qualityChartContainer");
  if (!qualityChartContainer) {
    qualityChartContainer = document.createElement("div");
    qualityChartContainer.id = "qualityChartContainer";
    qualityChartContainer.style.position = "relative";
    qualityChartContainer.style.height = "420px";
    qualityChartContainer.style.width = "100%";
    qualityChartContainer.innerHTML = '<canvas id="qualityChart" style="position: relative !important;"></canvas>';
    
    // Insert into the quality-card-content container
    const qualityContent = qualityCard.querySelector(".quality-card-content");
    qualityContent.appendChild(qualityChartContainer);
  }
  
  // Prepare signal data for chart
  const maxPoints = 2000;
  const signalData = downsample(
    cleanedSignalData.time,
    cleanedSignalData.values,
    maxPoints
  );
  
  // Create annotations for quality segments
  const annotations = {};
  
  // Add best segment highlighting (green)
  const bestStartTime = qualityData.best_segment_times[0];
  const bestEndTime = qualityData.best_segment_times[1];
  
  annotations.bestSegment = {
    type: "box",
    xMin: bestStartTime,
    xMax: bestEndTime,
    backgroundColor: "rgba(34, 197, 94, 0.4)",
    borderColor: "rgba(34, 197, 94, 0.8)",
    borderWidth: 3,
    label: {
      display: true,
      content: "Best Quality Segment",
      position: "start",
      backgroundColor: "rgba(34, 197, 94, 0.9)",
      color: "black",
      font: {
        weight: "bold",
        size: 10,
      },
      padding: 4,
    },
  };
  
  // Add bad segments (red shading)
  qualityData.bad_segment_times.forEach((badSegment, index) => {
    annotations[`badSegment${index}`] = {
      type: "box",
      xMin: badSegment[0],
      xMax: badSegment[1],
      backgroundColor: "rgba(239, 68, 68, 0.05)",
      borderColor: "rgba(239, 68, 68, 0.4)",
      borderWidth: 1,
      label: {
        display: index === 0, // Only show label on first bad segment
        content: "Poor Quality",
        position: "start",
        backgroundColor: "rgba(239, 68, 68, 0.9)",
        color: "black",
        font: {
          weight: "bold",
          size: 10,
        },
        padding: 4,
      },
    };
  });
  
  // Create quality chart
  const qualityCtx = document.getElementById("qualityChart");
  charts.quality = new Chart(qualityCtx, {
    type: "line",
    data: {
      labels: signalData.x,
      datasets: [
        {
          label: "Cleaned ECG Signal (Quality Assessment)",
          data: signalData.y,
          borderColor: "#6366f1",
          borderWidth: 1,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      hover: {
        intersect: false,
        animationDuration: 0
      },
      animation: false,
      plugins: {
        legend: {
          display: true,
          onClick: function() {
            // Disable legend click behavior to prevent dataset toggling
            return false;
          },
          onHover: function() {
            // Disable legend hover effects
            return false;
          },
          labels: {
            usePointStyle: false,
            boxWidth: 12,
            color: '#374151'
          }
        },
        annotation: {
          annotations: annotations,
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Time (seconds)",
          },
          type: "linear",
        },
        y: {
          title: {
            display: true,
            text: "Amplitude (mV)",
          },
        },
      }
    },
  });
  
  // Create or update quality summary table
  let qualityDetailsContainer = document.getElementById("qualityDetailsContainer");
  if (!qualityDetailsContainer) {
    qualityDetailsContainer = document.createElement("div");
    qualityDetailsContainer.id = "qualityDetailsContainer";
    qualityDetailsContainer.className = "quality-details";
    qualityChartContainer.insertAdjacentElement("afterend", qualityDetailsContainer);
  }
  
  // Create quality summary and details
  const summary = qualityData.summary;
  const windows = qualityData.windows;
  
  // Find the best window that corresponds to the best segment
  const bestWindow = windows.find(window => 
    window.start_time <= bestStartTime && window.end_time >= bestEndTime
  ) || windows.find(window => 
    Math.abs((window.start_time + window.end_time) / 2 - (bestStartTime + bestEndTime) / 2) < 5
  );
  
  qualityDetailsContainer.innerHTML = `
    <div class="quality-content-wrapper" style="display: flex !important; gap: 1rem; align-items: flex-start; flex-direction: row !important; border: 2px dashed #e2e8f0; padding: 1rem; background: #f9fafb;">
      <div class="quality-summary" style="background: #f8fafc; padding: 0.75rem; border-radius: 8px; border: 1px solid #6366f1; flex: 0 0 280px; max-width: 280px; font-size: 0.875rem;">
        <h4 style="font-size: 1rem; margin-bottom: 0.5rem; font-weight: 600;">Quality Assessment Summary</h4>
        <div class="quality-stats">
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Overall Status:</span>
            <span class="quality-value status-${summary.status.toLowerCase()}" style="font-weight: 600; font-size: 0.8rem;">${summary.status}</span>
          </div>
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Quality Rate:</span>
            <span class="quality-value" style="font-weight: 600; font-size: 0.8rem;">${summary.good_percentage.toFixed(1)}%</span>
          </div>
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Good Windows:</span>
            <span class="quality-value" style="font-weight: 600; font-size: 0.8rem;">${summary.good_windows}/${summary.total_windows}</span>
          </div>
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Best Segment:</span>
            <span class="quality-value" style="font-weight: 600; font-size: 0.8rem;">${bestStartTime.toFixed(2)}s - ${bestEndTime.toFixed(2)}s</span>
          </div>
          ${bestWindow ? `
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Best Window mSQI:</span>
            <span class="quality-value" style="font-weight: 600; font-size: 0.8rem;">${bestWindow.mSQI.toFixed(3)}</span>
          </div>
          <div class="quality-stat" style="display: flex; justify-content: space-between; align-items: center; padding: 0.375rem 0.5rem; margin-bottom: 0.25rem; background: white; border-radius: 4px; border: 1px solid #e2e8f0; font-size: 0.8rem;">
            <span class="quality-label" style="font-weight: 500; color: #64748b;">Best Window kSQI:</span>
            <span class="quality-value" style="font-weight: 600; font-size: 0.8rem;">${bestWindow.kSQI.toFixed(2)}</span>
          </div>
          ` : ''}
        </div>
      </div>
      
      <details class="quality-details-toggle" style="flex: 1; min-width: 500px; border: 1px solid #6366f1; border-radius: 8px; padding: 1rem; background: white; margin-left: 1rem;">
        <summary style="font-size: 1rem; font-weight: 600; cursor: pointer; padding: 0.5rem 0;">Detailed Window Analysis (${windows.length} windows)</summary>
        <div class="quality-table-container">
          <table class="quality-table">
            <thead>
              <tr>
                <th>Window</th>
                <th>Time Range (s)</th>
                <th>mSQI</th>
                <th>kSQI</th>
                <th>HR (bpm)</th>
                <th>SDNN</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${windows.map(window => `
                <tr class="quality-row status-${window.status.toLowerCase()}">
                  <td>${window.window}</td>
                  <td>${window.start_time.toFixed(1)} - ${window.end_time.toFixed(1)}</td>
                  <td>${window.mSQI.toFixed(3)}</td>
                  <td>${window.kSQI.toFixed(2)}</td>
                  <td>${window.heart_rate.toFixed(1)}</td>
                  <td>${window.sdnn.toFixed(2)}</td>
                  <td><span class="status-badge status-${window.status.toLowerCase()}">${window.status}</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  `;
}

// Destroy all charts
function destroyCharts() {
  Object.values(charts).forEach((chart) => {
    if (chart) {
      chart.destroy();
    }
  });
  charts = {};
}

// Show error message
function showError(message) {
  errorMessage.textContent = message;
  errorMessage.style.display = "block";
}

// Hide error message
function hideError() {
  errorMessage.style.display = "none";
  errorMessage.textContent = "";
}

// Set loading state
function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  if (isLoading) {
    btnText.style.display = "none";
    btnSpinner.style.display = "inline-block";
  } else {
    btnText.style.display = "inline";
    btnSpinner.style.display = "none";
  }
}

// Set analyze button loading state
function setAnalyzeLoading(isLoading) {
  analyzeBtn.disabled = isLoading;
  if (isLoading) {
    analyzeBtnText.style.display = "none";
    analyzeBtnSpinner.style.display = "inline-block";
  } else {
    analyzeBtnText.style.display = "inline";
    analyzeBtnSpinner.style.display = "none";
  }
}
