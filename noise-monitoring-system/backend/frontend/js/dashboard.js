if (!getToken()) {
  window.location.href = "index.html";
}

const user = getUser();
const isAdmin = user && (user.role === "administrator" || user.role === "system_admin");

document.getElementById("user-name").textContent = user ? user.full_name : "";
document.getElementById("user-role").textContent = user ? user.role.replace("_", " ") : "";
if (isAdmin) document.getElementById("admin-panel").classList.remove("hidden");

document.getElementById("logout-btn").addEventListener("click", () => {
  clearSession();
  window.location.href = "index.html";
});

let sensorsCache = [];

function fmtTime(iso) {
  if (!iso) return "no readings yet";
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function statusLabel(colour) {
  return { green: "Acceptable", yellow: "Elevated", red: "Excessive", "no-data": "No data" }[colour] || "Unknown";
}

// ---------------------------------------------------------
// Summary cards
// ---------------------------------------------------------
async function loadSummary() {
  try {
    const s = await apiFetch("/api/analytics/summary");
    document.getElementById("sum-sensors").textContent = `${s.sensors_active}/${s.sensors_total}`;
    document.getElementById("sum-avg").textContent = s.today_avg_db != null ? `${s.today_avg_db} dB` : "–";
    document.getElementById("sum-peak").textContent = s.today_peak_db != null ? `${s.today_peak_db} dB` : "–";
    document.getElementById("sum-pending").textContent = s.pending_alerts;
  } catch (err) {
    console.error("summary load failed", err);
  }
}

// ---------------------------------------------------------
// Live sensor cards
// ---------------------------------------------------------
async function loadLatestReadings() {
  try {
    const data = await apiFetch("/api/readings/latest");
    sensorsCache = data.readings;
    const grid = document.getElementById("sensor-grid");
    grid.innerHTML = "";

    if (!data.readings.length) {
      grid.innerHTML = `<p class="empty-note">No sensors registered yet.</p>`;
      return;
    }

    data.readings.forEach((r) => {
      const colour = r.status_colour || "no-data";
      const card = document.createElement("div");
      card.className = `sensor-card status-${colour}`;
      card.innerHTML = `
        <div class="loc">${r.location}</div>
        <div class="room">${r.room_identifier} · ${r.sensor_code}</div>
        <div><span class="db-value">${r.decibel_value != null ? Number(r.decibel_value).toFixed(1) : "–"}</span>
          <span class="db-unit">dB</span></div>
        <span class="status-tag status-${colour}">${statusLabel(colour)}</span>
        <span class="updated">Updated ${fmtTime(r.recorded_at)}</span>
      `;
      grid.appendChild(card);
    });

    syncSensorSelects(data.readings);
  } catch (err) {
    console.error("readings load failed", err);
  }
}

function syncSensorSelects(readings) {
  const chartSelect = document.getElementById("chart-sensor");
  const thSelect = document.getElementById("th-sensor");
  [chartSelect, thSelect].forEach((sel) => {
    if (!sel || sel.dataset.populated === "true") return;
  });

  if (chartSelect.options.length === 0) {
    readings.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.sensor_id;
      opt.textContent = `${r.location} (${r.sensor_code})`;
      chartSelect.appendChild(opt);
    });
    chartSelect.addEventListener("change", loadTrendChart);
    document.getElementById("chart-range").addEventListener("change", loadTrendChart);
    loadTrendChart();
  }

  if (thSelect && thSelect.options.length === 0) {
    readings.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.sensor_id;
      opt.textContent = `${r.location} (${r.sensor_code})`;
      thSelect.appendChild(opt);
    });
  }
}

// ---------------------------------------------------------
// Historical trend chart
// ---------------------------------------------------------
async function loadTrendChart() {
  const sensorId = document.getElementById("chart-sensor").value;
  const range = document.getElementById("chart-range").value;
  if (!sensorId) return;

  try {
    const data = await apiFetch(`/api/readings/history?sensor_id=${sensorId}&range=${range}`);
    const labels = data.readings.map((r) => {
      const d = new Date(r.recorded_at.endsWith("Z") ? r.recorded_at : r.recorded_at + "Z");
      return range === "week"
        ? d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit" })
        : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    });
    const values = data.readings.map((r) => Number(r.decibel_value));

    let thresholdValue = null;
    try {
      const th = await apiFetch(`/api/thresholds?sensor_id=${sensorId}`);
      if (th.thresholds.length) thresholdValue = Number(th.thresholds[0].max_decibel);
    } catch (_) { /* thresholds optional for chart overlay */ }

    renderTrendChart("trend-chart", labels, values, thresholdValue);
  } catch (err) {
    console.error("trend load failed", err);
  }
}

// ---------------------------------------------------------
// Alerts
// ---------------------------------------------------------
async function loadAlerts() {
  try {
    const data = await apiFetch("/api/alerts?status=pending");
    const list = document.getElementById("alerts-list");
    list.innerHTML = "";

    if (!data.alerts.length) {
      list.innerHTML = `<p class="empty-note">No active violations. All monitored spaces are within threshold.</p>`;
      return;
    }

    data.alerts.forEach((a) => {
      const item = document.createElement("div");
      item.className = "alert-item";
      item.innerHTML = `
        <div class="alert-loc">${a.location} · ${a.room_identifier}</div>
        <div class="alert-meta">${Number(a.decibel_value).toFixed(1)} dB (limit ${Number(a.max_decibel).toFixed(0)} dB) · triggered ${fmtTime(a.triggered_at)}</div>
        ${isAdmin ? `<button data-id="${a.id}" class="ack-btn">Acknowledge</button>` : ""}
      `;
      list.appendChild(item);
    });

    document.querySelectorAll(".ack-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          await apiFetch(`/api/alerts/${btn.dataset.id}/acknowledge`, { method: "POST" });
          loadAlerts();
          loadSummary();
        } catch (err) {
          alert(err.message);
          btn.disabled = false;
        }
      });
    });
  } catch (err) {
    console.error("alerts load failed", err);
  }
}

// ---------------------------------------------------------
// Admin: thresholds
// ---------------------------------------------------------
async function loadThresholds() {
  if (!isAdmin) return;
  try {
    const data = await apiFetch("/api/thresholds");
    const list = document.getElementById("thresholds-list");
    list.innerHTML = "";
    data.thresholds.forEach((t) => {
      const item = document.createElement("div");
      item.className = "threshold-item";
      item.innerHTML = `
        <div class="t-loc">${t.location} — ${Number(t.max_decibel).toFixed(0)} dB</div>
        <div class="t-meta">${t.period_start}–${t.period_end} · ${t.label}</div>
      `;
      list.appendChild(item);
    });
  } catch (err) {
    console.error("thresholds load failed", err);
  }
}

const thresholdForm = document.getElementById("threshold-form");
if (thresholdForm) {
  thresholdForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/api/thresholds", {
        method: "POST",
        body: JSON.stringify({
          sensor_id: Number(document.getElementById("th-sensor").value),
          max_decibel: Number(document.getElementById("th-max").value),
          period_start: document.getElementById("th-start").value + ":00",
          period_end: document.getElementById("th-end").value + ":00",
          label: "Custom threshold",
        }),
      });
      document.getElementById("th-max").value = "";
      loadThresholds();
    } catch (err) {
      alert(err.message);
    }
  });
}

// ---------------------------------------------------------
// Poll loop
// ---------------------------------------------------------
function refreshAll() {
  loadSummary();
  loadLatestReadings();
  loadAlerts();
  loadThresholds();
}

refreshAll();
setInterval(() => {
  loadSummary();
  loadLatestReadings();
  loadAlerts();
}, 5000);
