const presets = {
  harbour: { lat: -33.8568, lng: 151.2153, label: "Sydney Harbour" },
  bondi: { lat: -33.8915, lng: 151.2767, label: "Bondi Beach" },
  manly: { lat: -33.7969, lng: 151.2888, label: "Manly Beach" },
};

const state = {
  opportunity: null,
  agent: null,
  factorReport: null,
  stats: null,
};

const $ = (id) => document.getElementById(id);

function fmt(value, fallback = "--") {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value);
}

function nowIsoLocal() {
  const date = new Date();
  const offsetMin = -date.getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const hh = String(Math.floor(abs / 60)).padStart(2, "0");
  const mm = String(abs % 60).padStart(2, "0");
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}T${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:00${sign}${hh}:${mm}`;
}

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function checkApi() {
  try {
    await getJson("/health");
    $("apiDot").className = "status-dot ok";
    $("apiStatus").textContent = "API online";
  } catch (error) {
    $("apiDot").className = "status-dot bad";
    $("apiStatus").textContent = "API offline";
  }
}

function requestPayload() {
  const preset = presets[$("preset").value];
  return {
    location: { lat: preset.lat, lng: preset.lng },
    time: nowIsoLocal(),
    radius_m: 3000,
    subject: $("subject").value,
  };
}

async function runOpportunity() {
  $("runCheck").disabled = true;
  $("runCheck").textContent = "Running";
  const payload = requestPayload();
  $("timeValue").textContent = payload.time;
  try {
    const opportunity = await getJson("/opportunity", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.opportunity = opportunity;
    renderOpportunity(opportunity);
    try {
      const agent = await getJson("/agent/decide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.agent = agent;
      renderAgent(agent);
    } catch (error) {
      renderAgent({ status: "blocked", error: error.message, agent_decision: null });
    }
  } catch (error) {
    $("scoreStatus").textContent = "blocked";
    $("scoreReason").textContent = `Opportunity pipeline failed: ${error.message}`;
  } finally {
    $("runCheck").disabled = false;
    $("runCheck").textContent = "Run check";
    refreshSideData();
  }
}

function renderOpportunity(data) {
  const score = data.score || {};
  $("scoreValue").textContent = fmt(score.score);
  $("scoreStatus").textContent = score.status || "unknown";
  $("windowValue").textContent = score.window || "window unavailable";
  $("directionValue").textContent = score.direction || "direction unavailable";
  $("scoreReason").textContent = score.reason || "No reason returned.";

  const features = data.photographic_features || {};
  const featureKeys = [
    "golden_hour",
    "blue_hour",
    "sun_direction",
    "high_cloud_cover",
    "low_cloud_cover",
    "visibility_km",
    "direction_match_score",
    "water_reflection_score",
    "spot_subject_match_score",
    "travel_cost_score",
  ];
  $("featureRows").innerHTML = featureKeys
    .map((key) => `<div class="row"><span>${key}</span><strong>${fmt(features[key])}</strong></div>`)
    .join("");

  const connectors = [
    ["Open-Meteo weather", data.weather],
    ["SunCalc astronomy", data.astronomy],
    ["OpenStreetMap geo", data.geo],
    ["Spot repository", data.spots],
  ];
  $("connectorRows").innerHTML = connectors
    .map(([label, item]) => `<div class="connector-row"><span>${label}</span><strong>${item?.ok ? "ok" : item?.error || "blocked"}</strong></div>`)
    .join("");
}

function renderAgent(data) {
  const decision = data.agent_decision || {};
  const status = decision.status || data.status || "blocked";
  $("agentStatus").textContent = status;
  $("agentMessage").textContent = decision.message || data.error || data.failure_state || "No Agent message returned.";
  $("agentSpot").textContent = `Spot ${decision.recommended_spot || "--"}`;
  $("agentLead").textContent = `Lead ${fmt(decision.notify_lead_minutes)} min`;
}

async function refreshSideData() {
  const [loop, stats, report] = await Promise.allSettled([
    getJson("/loop/status"),
    getJson("/opportunity-db/stats"),
    getJson("/factor-research/report"),
  ]);
  if (loop.status === "fulfilled") renderLoop(loop.value);
  if (stats.status === "fulfilled") {
    state.stats = stats.value;
    renderStats(stats.value);
  }
  if (report.status === "fulfilled") {
    state.factorReport = report.value;
    renderFactors(report.value);
  }
}

function renderLoop(data) {
  const rows = data.recent_runs || [];
  $("loopRows").innerHTML = rows.length
    ? rows.slice(0, 5).map((row) => `<div class="timeline-row"><span>${row.created_at}</span><strong>${row.status}</strong></div>`).join("")
    : `<div class="timeline-row"><span>No persisted loop runs yet</span><strong>${data.running ? "running" : "idle"}</strong></div>`;
}

function renderStats(stats) {
  $("sampleCount").textContent = fmt(stats.spot_photo_samples);
  $("contextCount").textContent = fmt(stats.photo_spot_context_enrichment);
  $("remainingCount").textContent = fmt(stats.remaining_unenriched);
}

function renderFactors(report) {
  const factors = report.factors || [];
  $("factorCards").innerHTML = factors.map((factor) => {
    const conditions = (factor.conditions || [])
      .map((c) => `<span class="condition">${c.field} ${c.op} ${c.value}</span>`)
      .join("");
    return `<article class="factor-card">
      <p class="label">${factor.status || "candidate"} · ${factor.validation_unit || "unknown unit"}</p>
      <h3>${factor.factor_id}</h3>
      <div class="conditions">${conditions}</div>
      <div class="factor-stats">
        <div class="factor-stat"><span>samples</span><strong>${fmt(factor.sample_size)}</strong></div>
        <div class="factor-stat"><span>eligible</span><strong>${fmt(factor.eligible_sample_size)}</strong></div>
        <div class="factor-stat"><span>matches</span><strong>${fmt(factor.matches)}</strong></div>
        <div class="factor-stat"><span>hit rate</span><strong>${fmt(factor.hit_rate)}</strong></div>
        <div class="factor-stat"><span>lift</span><strong>${fmt(factor.lift)}</strong></div>
      </div>
    </article>`;
  }).join("");
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      const view = button.dataset.view;
      $(`${view}View`).classList.add("active");
      $("viewTitle").textContent = view === "research" ? "Factor Research Studio" : view === "ops" ? "Precision Operations Console" : button.textContent;
    });
  });
}

bindNavigation();
$("runCheck").addEventListener("click", runOpportunity);
$("refreshResearch").addEventListener("click", refreshSideData);
checkApi();
refreshSideData();
