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

// Chart instances
let charts = {};

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

// Form submit handler
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  // Hide any previous errors
  hideError();

  // Get form data
  const formData = new FormData();
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

  // Add file to form data
  formData.append("file", file);

  // Add optional parameters
  const duration = document.getElementById("duration").value;
  if (duration) {
    formData.append("duration", duration);
  }

  const channels = document.getElementById("channels").value;
  if (channels) {
    formData.append("channels", channels);
  }

  const samplingRate = document.getElementById("samplingRate").value;
  if (samplingRate) {
    formData.append("sampling_rate", samplingRate);
  }

  const includeSignals = document.getElementById("includeSignals").checked;
  formData.append("include_signals", includeSignals);

  // Show loading state
  setLoading(true);

  try {
    // Call API
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
    setLoading(false);
  }
});

// New analysis button handler
newAnalysisBtn.addEventListener("click", () => {
  // Reset form
  uploadForm.reset();
  fileName.textContent = "Choose ECG file (.txt)";
  fileLabel.classList.remove("has-file");

  // Hide results
  resultsSection.style.display = "none";

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
