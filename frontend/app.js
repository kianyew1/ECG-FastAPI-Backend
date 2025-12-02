// DOM Elements - Core functionality only
const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const fileName = document.getElementById("fileName");
const fileLabel = document.querySelector(".file-label");
const submitBtn = document.getElementById("submitBtn");
const errorMessage = document.getElementById("errorMessage");
const resultsSection = document.getElementById("resultsSection");
const timeframeSection = document.getElementById("timeframeSection");
const channelSelect = document.getElementById("channelSelect");
// const previewCard = document.getElementById("previewCard"); // Removed
const startTimeSlider = document.getElementById("startTimeSlider");
const endTimeSlider = document.getElementById("endTimeSlider");
const analyzeBtn = document.getElementById("analyzeBtn");

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
  document.getElementById("resultsSection").style.display = "none";
  document.getElementById("timeframeSection").style.display = "none";

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
  document.getElementById("startTimeValue").textContent = "0.00";
  document.getElementById("endTimeValue").textContent = maxDuration.toFixed(2);

  // Update sampling rate from input (or use default)
  samplingRate = parseInt(document.getElementById("samplingRate").value) || 500;
  updateSelectedDuration();

  // Show timeframe section
  document.getElementById("timeframeSection").style.display = "block";
  document
    .getElementById("timeframeSection")
    .scrollIntoView({ behavior: "smooth", block: "start" });

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
    document.getElementById("qualityCard").style.display = "none";
  }
});

// Load channel preview - fetches data for specific channel
async function loadChannelPreview(channel) {
  if (!currentFile) return;

  // Show loading state on quality card
  const qualityCard = document.getElementById("qualityCard");
  qualityCard.style.display = "block";

  // Add a loading indicator to quality chart container
  const qualityChartContainer = document.getElementById(
    "qualityChartContainer"
  );
  qualityChartContainer.style.display = "block";

  // Clear previous chart if exists
  if (charts.quality) {
    charts.quality.destroy();
    charts.quality = null;
  }

  // Remove any existing loading div
  const existingLoading = document.getElementById("previewLoading");
  if (existingLoading) existingLoading.remove();

  const loadingDiv = document.createElement("div");
  loadingDiv.id = "previewLoading";
  loadingDiv.className = "loading-overlay";
  loadingDiv.innerHTML =
    '<div class="spinner"></div><p>Loading channel quality check...</p>';
  qualityChartContainer.appendChild(loadingDiv);

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
    if (loadingDiv) loadingDiv.remove();

    // Display quality assessment if available
    if (channelData.quality_assessment) {
      displayQualityAssessment(
        channelData.quality_assessment,
        channelData.cleaned_signal
      );
    } else {
      // Handle case where no quality assessment is returned but we have signal
      console.warn("No quality assessment data returned");
      qualityCard.style.display = "none";
    }
  } catch (error) {
    console.error("Error loading channel preview:", error);
    showError(`Failed to load preview for ${channel}: ${error.message}`);

    // Remove loading indicator
    if (loadingDiv) loadingDiv.remove();
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

  document.getElementById("startTimeValue").textContent = parseFloat(
    e.target.value
  ).toFixed(2);
  updateSelectedDuration();
  updateQualityAnnotations();
});

endTimeSlider.addEventListener("input", (e) => {
  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(e.target.value);

  // Ensure end is after start
  if (endTime <= startTime) {
    e.target.value = Math.min(maxDuration, startTime + 0.1);
  }

  document.getElementById("endTimeValue").textContent = parseFloat(
    e.target.value
  ).toFixed(2);
  updateSelectedDuration();
  updateQualityAnnotations();
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

  document.getElementById("selectedDuration").textContent = duration.toFixed(2);
  document.getElementById("selectedSamples").textContent =
    samples.toLocaleString();
}

// Update quality chart annotations
function updateQualityAnnotations() {
  if (!charts.quality || !charts.quality.options.plugins.annotation) return;

  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);

  const annotations = charts.quality.options.plugins.annotation.annotations;

  // Update selection box
  if (annotations.selectionBox) {
    annotations.selectionBox.xMin = startTime;
    annotations.selectionBox.xMax = endTime;
  }

  // Update start line
  if (annotations.startLine) {
    annotations.startLine.xMin = startTime;
    annotations.startLine.xMax = startTime;
    annotations.startLine.label.content = `Start: ${startTime.toFixed(2)}s`;
  }

  // Update end line
  if (annotations.endLine) {
    annotations.endLine.xMin = endTime;
    annotations.endLine.xMax = endTime;
    annotations.endLine.label.content = `End: ${endTime.toFixed(2)}s`;
  }

  // Update chart with animation disabled for smooth dragging
  charts.quality.update("none");
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
document.getElementById("newAnalysisBtn").addEventListener("click", () => {
  // Reset form
  uploadForm.reset();
  document.getElementById("fileName").textContent = "Choose ECG file (.txt)";
  document.querySelector(".file-label").classList.remove("has-file");

  // Hide sections
  document.getElementById("resultsSection").style.display = "none";
  document.getElementById("timeframeSection").style.display = "none";
  document.getElementById("aimclubSection").style.display = "none";
  document.getElementById("aimclubResults").style.display = "none";
  // document.getElementById("previewCard").style.display = "none"; // Removed

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
  document.getElementById("resultsSection").style.display = "block";

  // Show aimclub section (below results)
  document.getElementById("aimclubSection").style.display = "block";

  // Handle charts if signals are included
  if (includeSignals && data.raw_signal) {
    document.getElementById("chartsSection").style.display = "block";
    destroyResultCharts(); // Clear any existing result charts but preserve preview/quality
    createCharts(data);
  } else {
    document.getElementById("chartsSection").style.display = "none";
  }

  // Scroll to results
  document
    .getElementById("resultsSection")
    .scrollIntoView({ behavior: "smooth", block: "start" });
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

  // Setup and show chart container (already exists in HTML)
  const qualityChartContainer = document.getElementById(
    "qualityChartContainer"
  );
  qualityChartContainer.style.display = "block";

  // Show quality details container
  const qualityDetailsContainer = document.getElementById(
    "qualityDetailsContainer"
  );
  qualityDetailsContainer.style.display = "block";

  // Create quality chart
  createQualityChart(qualityData, cleanedSignalData);

  // Populate quality summary
  populateQualitySummary(qualityData);

  // Populate quality table
  populateQualityTable(qualityData);
}

// Create quality chart
function createQualityChart(qualityData, cleanedSignalData) {
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

  // Add selection annotations
  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);

  annotations.selectionBox = {
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
  };

  annotations.startLine = {
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
  };

  annotations.endLine = {
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
        mode: "index",
      },
      hover: {
        intersect: false,
        animationDuration: 0,
      },
      animation: false,
      plugins: {
        legend: {
          display: true,
          onClick: function () {
            // Disable legend click behavior to prevent dataset toggling
            return false;
          },
          onHover: function () {
            // Disable legend hover effects
            return false;
          },
          labels: {
            usePointStyle: false,
            boxWidth: 12,
            color: "#374151",
          },
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
      },
    },
  });
}

// Populate quality summary
function populateQualitySummary(qualityData) {
  const summary = qualityData.summary;
  const windows = qualityData.windows;
  const bestStartTime = qualityData.best_segment_times[0];
  const bestEndTime = qualityData.best_segment_times[1];

  // Find the best window
  const bestWindow =
    windows.find(
      (window) =>
        window.start_time <= bestStartTime && window.end_time >= bestEndTime
    ) ||
    windows.find(
      (window) =>
        Math.abs(
          (window.start_time + window.end_time) / 2 -
            (bestStartTime + bestEndTime) / 2
        ) < 5
    );

  const qualityStats = document.getElementById("qualityStats");

  // Create stats elements iteratively
  const stats = [
    {
      label: "Overall Status:",
      value: summary.status,
      className: `status-${summary.status.toLowerCase()}`,
    },
    {
      label: "Quality Rate:",
      value: `${summary.good_percentage.toFixed(1)}%`,
    },
    {
      label: "Good Windows:",
      value: `${summary.good_windows}/${summary.total_windows}`,
    },
    {
      label: "Best Segment:",
      value: `${bestStartTime.toFixed(2)}s - ${bestEndTime.toFixed(2)}s`,
    },
  ];

  // Add best window stats if available
  if (bestWindow) {
    stats.push(
      {
        label: "Best Window mSQI:",
        value: bestWindow.mSQI.toFixed(3),
      },
      {
        label: "Best Window kSQI:",
        value: bestWindow.kSQI.toFixed(2),
      }
    );
  }

  // Clear existing stats
  qualityStats.innerHTML = "";

  // Create stat elements
  stats.forEach((stat) => {
    const statDiv = document.createElement("div");
    statDiv.className = "quality-stat";

    const labelSpan = document.createElement("span");
    labelSpan.className = "quality-label";
    labelSpan.textContent = stat.label;

    const valueSpan = document.createElement("span");
    valueSpan.className = stat.className
      ? `quality-value ${stat.className}`
      : "quality-value";
    valueSpan.textContent = stat.value;

    statDiv.appendChild(labelSpan);
    statDiv.appendChild(valueSpan);
    qualityStats.appendChild(statDiv);
  });
}

// Populate quality table
function populateQualityTable(qualityData) {
  const windows = qualityData.windows;
  const tableBody = document.getElementById("qualityTableBody");
  const detailsSummary = document.getElementById("qualityDetailsSummary");

  // Update summary text
  detailsSummary.textContent = `Detailed Window Analysis (${windows.length} windows)`;

  // Clear existing rows
  tableBody.innerHTML = "";

  // Create rows iteratively
  windows.forEach((window) => {
    const row = document.createElement("tr");
    row.className = `quality-row status-${window.status.toLowerCase()}`;

    // Create cells
    const cells = [
      window.window,
      `${window.start_time.toFixed(1)} - ${window.end_time.toFixed(1)}`,
      window.mSQI.toFixed(3),
      window.kSQI.toFixed(2),
      window.heart_rate.toFixed(1),
      window.sdnn.toFixed(2),
    ];

    cells.forEach((cellContent) => {
      const cell = document.createElement("td");
      cell.textContent = cellContent;
      row.appendChild(cell);
    });

    // Create status cell with badge
    const statusCell = document.createElement("td");
    const statusBadge = document.createElement("span");
    statusBadge.className = `status-badge status-${window.status.toLowerCase()}`;
    statusBadge.textContent = window.status;
    statusCell.appendChild(statusBadge);
    row.appendChild(statusCell);

    tableBody.appendChild(row);
  });
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

// Destroy only result charts (preserve preview and quality charts)
function destroyResultCharts() {
  ["raw", "cleaned", "heartRate", "rPeaks"].forEach((chartKey) => {
    if (charts[chartKey]) {
      charts[chartKey].destroy();
      delete charts[chartKey];
    }
  });
}

// Show error message
function showError(message) {
  const errorMessage = document.getElementById("errorMessage");
  errorMessage.textContent = message;
  errorMessage.style.display = "block";
}

// Hide error message
function hideError() {
  const errorMessage = document.getElementById("errorMessage");
  errorMessage.style.display = "none";
  errorMessage.textContent = "";
}

// Set loading state
function setLoading(isLoading) {
  const submitBtn = document.getElementById("submitBtn");
  const btnText = document.getElementById("btnText");
  const btnSpinner = document.getElementById("btnSpinner");

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
  const analyzeBtn = document.getElementById("analyzeBtn");
  const analyzeBtnText = document.getElementById("analyzeBtnText");
  const analyzeBtnSpinner = document.getElementById("analyzeBtnSpinner");

  analyzeBtn.disabled = isLoading;
  if (isLoading) {
    analyzeBtnText.style.display = "none";
    analyzeBtnSpinner.style.display = "inline-block";
  } else {
    analyzeBtnText.style.display = "inline";
    analyzeBtnSpinner.style.display = "none";
  }
}

// AimClub Analysis Button Handler
document.getElementById("runAimclubBtn").addEventListener("click", async () => {
  if (!currentFile) {
    showError("No file loaded. Please start over.");
    return;
  }

  const startTime = parseFloat(startTimeSlider.value);
  const endTime = parseFloat(endTimeSlider.value);
  const duration = endTime - startTime;
  const includeNN = document.getElementById("includeNN").checked;

  // Validate minimum duration for aimclub (5 seconds)
  if (duration < 5.0) {
    showError(
      "AimClub analysis requires at least 5 seconds of data. Please adjust your timeframe selection."
    );
    return;
  }

  // Show loading state
  setAimclubLoading(true);

  try {
    // Create form data
    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("duration", duration.toString());
    formData.append("include_nn", includeNN.toString());

    const response = await fetch("/api/analyze-aimclub", {
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

    if (!data.success) {
      throw new Error(data.error || "Analysis failed");
    }

    // Display aimclub results
    displayAimclubResults(data);
  } catch (error) {
    console.error("Error:", error);
    showError(`AimClub analysis failed: ${error.message}`);
  } finally {
    setAimclubLoading(false);
  }
});

// Display AimClub results
function displayAimclubResults(data) {
  // Show results container
  document.getElementById("aimclubResults").style.display = "block";

  // Signal information
  const info = data.signal_info;
  document.getElementById("aimclubChannels").textContent =
    info.original_channels;
  document.getElementById("aimclubLeads").textContent = info.converted_leads;
  document.getElementById("aimclubSamples").textContent =
    info.samples.toLocaleString();
  document.getElementById(
    "aimclubDuration"
  ).textContent = `${info.duration_seconds.toFixed(2)}s`;

  // ST-Elevation Classic
  const stClassic = data.st_elevation_classic;
  if (stClassic.success) {
    const status = stClassic.st_elevation_detected.toLowerCase();
    document.getElementById("stClassicStatus").textContent =
      stClassic.st_elevation_detected;
    document.getElementById("stClassicStatus").className = `result-status ${
      status === "normal" ? "normal" : "abnormal"
    }`;
    document.getElementById("stClassicExplanation").textContent =
      stClassic.explanation;
  }

  // ST-Elevation Neural Network
  if (data.st_elevation_nn) {
    const stNN = data.st_elevation_nn;
    document.getElementById("stNNBox").style.display = "block";
    if (stNN.success) {
      const status = stNN.st_elevation_detected.toLowerCase();
      document.getElementById("stNNStatus").textContent =
        stNN.st_elevation_detected;
      document.getElementById("stNNStatus").className = `result-status ${
        status === "normal" ? "normal" : "abnormal"
      }`;
      document.getElementById("stNNExplanation").textContent = stNN.explanation;
    }
  }

  // Risk Markers
  const risk = data.risk_markers;
  if (risk.success) {
    document.getElementById("aimclubQTc").textContent = risk.QTc_ms.toFixed(1);
    document.getElementById("aimclubRAV4").textContent =
      risk.RA_V4_mv.toFixed(3);
    document.getElementById("aimclubSTE60").textContent =
      risk.STE60_V3_mv.toFixed(3);
  }

  // Differential Diagnosis - Risk Markers
  const diagRisk = data.diagnosis_risk_markers;
  if (diagRisk.success) {
    const diagnosis = diagRisk.diagnosis.toLowerCase();
    document.getElementById("diagRiskStatus").textContent = diagRisk.diagnosis;
    document.getElementById("diagRiskStatus").className = `result-status ${
      diagnosis === "normal" ? "normal" : "abnormal"
    }`;
    document.getElementById("diagRiskExplanation").textContent =
      diagRisk.explanation;
  }

  // Differential Diagnosis - Neural Network
  if (data.diagnosis_nn) {
    const diagNN = data.diagnosis_nn;
    document.getElementById("diagNNBox").style.display = "block";
    if (diagNN.success) {
      document.getElementById("diagBER").textContent = diagNN.ber_detected
        ? `Detected - ${diagNN.ber_explanation}`
        : `Not Detected - ${diagNN.ber_explanation}`;
      document.getElementById("diagMI").textContent = diagNN.mi_detected
        ? `Detected - ${diagNN.mi_explanation}`
        : `Not Detected - ${diagNN.mi_explanation}`;
    }
  }

  // QRS Complex
  const qrs = data.qrs_complex;
  const qrsSummary = document.getElementById("qrsSummary");
  if (qrs.success) {
    let qrsHtml = `<p><strong>Channels analyzed:</strong> ${qrs.qrs_peaks_detected}</p>`;

    if (qrs.peaks_summary && qrs.peaks_summary.length > 0) {
      // Show first 3 channels with detailed wave info
      const channelsToShow = qrs.peaks_summary.slice(0, 3);
      channelsToShow.forEach((channel) => {
        qrsHtml += `<div class="qrs-channel">`;
        qrsHtml += `<h5>Channel ${channel.channel}</h5>`;
        qrsHtml += `<div class="qrs-waves">`;
        for (const [wave, data] of Object.entries(channel.waves)) {
          qrsHtml += `<div class="qrs-wave-item"><strong>${wave}:</strong> ${data.count} peaks</div>`;
        }
        qrsHtml += `</div></div>`;
      });

      if (qrs.peaks_summary.length > 3) {
        qrsHtml += `<p style="margin-top: 1rem; color: var(--text-secondary); font-style: italic;">+ ${
          qrs.peaks_summary.length - 3
        } more channels analyzed</p>`;
      }
    }

    qrsSummary.innerHTML = qrsHtml;
  } else {
    qrsSummary.innerHTML = `<p style="color: var(--error-color);">QRS analysis failed: ${qrs.error}</p>`;
  }

  // Scroll to aimclub section
  document
    .getElementById("aimclubSection")
    .scrollIntoView({ behavior: "smooth", block: "start" });
}

// Set aimclub button loading state
function setAimclubLoading(isLoading) {
  const btn = document.getElementById("runAimclubBtn");
  const btnText = document.getElementById("aimclubBtnText");
  const btnSpinner = document.getElementById("aimclubBtnSpinner");

  btn.disabled = isLoading;
  if (isLoading) {
    btnText.style.display = "none";
    btnSpinner.style.display = "inline-block";
  } else {
    btnText.style.display = "inline";
    btnSpinner.style.display = "none";
  }
}
