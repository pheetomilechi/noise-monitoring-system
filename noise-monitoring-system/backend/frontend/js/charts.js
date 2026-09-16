let trendChart = null;

function renderTrendChart(canvasId, labels, values, thresholdValue) {
  const ctx = document.getElementById(canvasId).getContext("2d");

  const datasets = [
    {
      label: "Noise level (dB)",
      data: values,
      borderColor: "#3FBFAE",
      backgroundColor: "rgba(63,191,174,0.12)",
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
    },
  ];

  if (thresholdValue) {
    datasets.push({
      label: "Threshold",
      data: labels.map(() => thresholdValue),
      borderColor: "#E15D5D",
      borderDash: [6, 4],
      borderWidth: 1.5,
      pointRadius: 0,
      fill: false,
    });
  }

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#8A9BAC", font: { family: "Inter" } } },
      },
      scales: {
        x: { ticks: { color: "#8A9BAC", maxTicksLimit: 8 }, grid: { color: "#263241" } },
        y: { ticks: { color: "#8A9BAC" }, grid: { color: "#263241" }, title: { display: true, text: "dB", color: "#8A9BAC" } },
      },
    },
  });
}
