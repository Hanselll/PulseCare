const services = [
  { id: "ingestion", name: "ingestion-service", url: "/api/ingestion/healthz" },
  { id: "scoring", name: "risk-scoring-service", url: "/api/scoring/healthz" },
  { id: "alert", name: "alert-service", url: "/api/alerts/healthz" },
  { id: "simulator", name: "device-simulator", url: "/api/simulator/healthz" },
];

const riskPalette = {
  LOW: "#34d399",
  MEDIUM: "#fbbf24",
  HIGH: "#fb923c",
  CRITICAL: "#fb7185",
};

const devices = Array.from({ length: 25 }, (_, index) => ({
  id: `dev-${String(index + 1).padStart(3, "0")}`,
  region: `gz-edge-${(index % 3) + 1}`,
}));

const state = {
  serviceHealth: [],
  alerts: [],
  riskCounts: { LOW: 18, MEDIUM: 5, HIGH: 2, CRITICAL: 0 },
  eventRate: null,
};

const $ = (selector) => document.querySelector(selector);

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function queryPrometheus(query) {
  const data = await fetchJson(`/prometheus/api/v1/query?query=${encodeURIComponent(query)}`);
  return data?.data?.result ?? [];
}

async function refresh() {
  await Promise.allSettled([loadServices(), loadAlerts(), loadMetrics()]);
  render();
}

async function loadServices() {
  const results = await Promise.allSettled(
    services.map(async (service) => {
      const payload = await fetchJson(service.url);
      return { ...service, healthy: payload.status === "ok", detail: payload.service };
    }),
  );

  state.serviceHealth = results.map((result, index) => {
    if (result.status === "fulfilled") {
      return result.value;
    }
    return { ...services[index], healthy: false, detail: "unreachable" };
  });
}

async function loadAlerts() {
  try {
    const payload = await fetchJson("/api/alerts/api/v1/alerts?limit=30");
    state.alerts = payload.alerts ?? [];
  } catch {
    state.alerts = [];
  }
}

async function loadMetrics() {
  try {
    const [eventRateResult, riskResult] = await Promise.all([
      queryPrometheus("sum(rate(pulsecare_simulator_events_total[1m]))"),
      queryPrometheus("sum by (risk_level) (increase(pulsecare_scoring_risk_level_total[15m]))"),
    ]);

    const eventValue = Number(eventRateResult?.[0]?.value?.[1] ?? 0);
    state.eventRate = Number.isFinite(eventValue) ? eventValue : null;

    const nextRiskCounts = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    for (const item of riskResult) {
      const level = item.metric?.risk_level;
      if (level in nextRiskCounts) {
        nextRiskCounts[level] = Math.round(Number(item.value?.[1] ?? 0));
      }
    }

    const total = Object.values(nextRiskCounts).reduce((sum, value) => sum + value, 0);
    if (total > 0) {
      state.riskCounts = nextRiskCounts;
    }
  } catch {
    state.eventRate = null;
  }
}

function render() {
  renderSummary();
  renderServices();
  renderRisks();
  renderDevices();
  renderAlerts();
}

function renderSummary() {
  const healthy = state.serviceHealth.filter((service) => service.healthy).length;
  const allHealthy = healthy === services.length;
  const openAlerts = state.alerts.filter((alert) => alert.status === "OPEN").length;

  $("#healthy-services").textContent = `${healthy}/${services.length}`;
  $("#device-count").textContent = String(devices.length);
  $("#event-rate").textContent =
    state.eventRate === null ? "--/s" : `${state.eventRate.toFixed(2)}/s`;
  $("#open-alerts").textContent = String(openAlerts);
  $("#global-status").textContent = allHealthy ? "运行正常" : "需要关注";
  $("#last-refresh").textContent = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  $("#global-dot").className = `dot ${allHealthy ? "ok" : "crit"}`;
}

function renderServices() {
  $("#service-chain").innerHTML = state.serviceHealth
    .map(
      (service) => `
        <article class="service-card">
          <div class="status-line">
            <span class="dot ${service.healthy ? "ok" : "crit"}"></span>
            <span>${service.healthy ? "healthy" : "unreachable"}</span>
          </div>
          <strong>${service.name}</strong>
          <small>${service.detail}</small>
        </article>
      `,
    )
    .join("");
}

function renderRisks() {
  const total = Math.max(1, Object.values(state.riskCounts).reduce((sum, value) => sum + value, 0));
  $("#risk-bars").innerHTML = Object.entries(state.riskCounts)
    .map(([level, count]) => {
      const width = Math.max(3, Math.round((count / total) * 100));
      return `
        <div class="risk-bar">
          <header><span>${level}</span><strong>${count}</strong></header>
          <div class="track"><div class="fill" style="width: ${width}%; background: ${riskPalette[level]}"></div></div>
        </div>
      `;
    })
    .join("");
}

function renderDevices() {
  const alertByDevice = new Map();
  for (const alert of state.alerts) {
    if (alert.device_id && !alertByDevice.has(alert.device_id)) {
      alertByDevice.set(alert.device_id, alert);
    }
  }

  $("#device-grid").innerHTML = devices
    .map((device, index) => {
      const alert = alertByDevice.get(device.id);
      const level = classifyDevice(alert, index);
      const score = level === "CRITICAL" ? 24 : level === "HIGH" ? 48 : level === "MEDIUM" ? 72 : 94;
      return `
        <article class="device-card ${level.toLowerCase()}">
          <div>
            <strong>${device.id}</strong>
            <small>${device.region}</small>
          </div>
          <div class="device-score">
            <span>${level}</span>
            <b>${score}</b>
          </div>
        </article>
      `;
    })
    .join("");
}

function classifyDevice(alert, index) {
  if (!alert) {
    return index % 11 === 0 ? "MEDIUM" : "LOW";
  }
  if (String(alert.severity).toLowerCase().includes("critical")) {
    return "CRITICAL";
  }
  return "HIGH";
}

function renderAlerts() {
  $("#alert-count").textContent = `${state.alerts.length} 条`;

  if (state.alerts.length === 0) {
    $("#alert-list").innerHTML = '<div class="empty">暂无告警。切换 simulator ERROR_MODE 后这里会出现实时告警。</div>';
    return;
  }

  $("#alert-list").innerHTML = state.alerts
    .slice(0, 12)
    .map((alert) => {
      const severity = String(alert.severity ?? "warning");
      const createdAt = alert.created_at ? new Date(alert.created_at).toLocaleString("zh-CN") : "--";
      return `
        <article class="alert-row">
          <div>
            <strong>${alert.device_id ?? alert.region}</strong>
            <span>${createdAt}</span>
          </div>
          <div>
            <strong>${alert.reason}</strong>
            <span>${alert.alert_id}</span>
          </div>
          <strong class="severity ${severity.toLowerCase()}">${severity}</strong>
        </article>
      `;
    })
    .join("");
}

$("#refresh-button").addEventListener("click", refresh);
refresh();
setInterval(refresh, 5000);
