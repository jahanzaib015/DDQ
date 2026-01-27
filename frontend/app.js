const apiBaseInput = document.getElementById("apiBase");
const saveApiBaseBtn = document.getElementById("saveApiBase");
const apiStatus = document.getElementById("apiStatus");
const uploadForm = document.getElementById("uploadForm");
const messageEl = document.getElementById("message");
const resultsSection = document.getElementById("resultsSection");
const summaryEl = document.getElementById("summary");
const reportTableBody = document.querySelector("#reportTable tbody");
const downloadCsvBtn = document.getElementById("downloadCsv");
const downloadJsonBtn = document.getElementById("downloadJson");

let lastCsv = "";
let lastSummaryJson = "";

function getApiBaseFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const api = params.get("api");
  return api ? api.replace(/\/$/, "") : "";
}

function getStoredApiBase() {
  return localStorage.getItem("ddq_api_base") || "";
}

function setApiStatus(base) {
  if (!base) {
    apiStatus.textContent = "API not set";
    apiStatus.classList.remove("ok");
    return;
  }
  apiStatus.textContent = base;
  apiStatus.classList.add("ok");
}

function setMessage(text, type = "info") {
  messageEl.textContent = text;
  messageEl.className = `message ${type}`;
}

function clearMessage() {
  messageEl.textContent = "";
  messageEl.className = "message hidden";
}

function hydrateApiBase() {
  const fromUrl = getApiBaseFromUrl();
  const stored = getStoredApiBase();
  const origin = window.location.origin && window.location.origin !== "null"
    ? window.location.origin
    : "";
  const base = fromUrl || stored || origin;
  apiBaseInput.value = base;
  setApiStatus(base);
}

saveApiBaseBtn.addEventListener("click", () => {
  const base = apiBaseInput.value.trim().replace(/\/$/, "");
  localStorage.setItem("ddq_api_base", base);
  setApiStatus(base);
  setMessage("API Base URL saved.", "success");
});

downloadCsvBtn.addEventListener("click", () => {
  if (!lastCsv) return;
  const blob = new Blob([lastCsv], { type: "text/csv;charset=utf-8" });
  triggerDownload(blob, "report.csv");
});

downloadJsonBtn.addEventListener("click", () => {
  if (!lastSummaryJson) return;
  const blob = new Blob([lastSummaryJson], { type: "application/json" });
  triggerDownload(blob, "summary.json");
});

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderSummary(summary) {
  if (!summary) {
    summaryEl.innerHTML = "";
    return;
  }
  const byStatus = summary.by_status || {};
  const items = Object.entries(byStatus)
    .map(([status, count]) => `<span class="badge">${status}: ${count}</span>`)
    .join("");

  summaryEl.innerHTML = `
    <div class="summary-card">
      <div><strong>Total rows:</strong> ${summary.total_rows}</div>
      <div><strong>Total flagged:</strong> ${summary.total_flagged}</div>
      <div class="summary-badges">${items}</div>
    </div>
  `;
}

function renderReportRows(rows) {
  reportTableBody.innerHTML = "";
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.sheet || "")}</td>
      <td>${escapeHtml(String(row.row_idx ?? ""))}</td>
      <td>${escapeHtml(row.question_id || "")}</td>
      <td><span class="pill ${statusClass(row.status)}">${escapeHtml(row.status || "")}</span></td>
      <td>${escapeHtml(row.reason || "")}</td>
      <td>${escapeHtml(row.question_text || "")}</td>
      <td>${escapeHtml(row.answer_text || "")}</td>
      <td>${escapeHtml(row.expected_text || "")}</td>
    `;
    reportTableBody.appendChild(tr);
  });
}

function statusClass(status) {
  if (!status) return "";
  const normalized = status.toLowerCase();
  if (normalized === "ok") return "ok";
  if (normalized === "skipped") return "skipped";
  return "flagged";
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearMessage();

  const apiBase = apiBaseInput.value.trim().replace(/\/$/, "");
  const resolvedApiBase = apiBase || (window.location.origin !== "null" ? window.location.origin : "");
  if (!resolvedApiBase) {
    setMessage("Please set the API Base URL first.", "error");
    return;
  }

  const fileInput = document.getElementById("fileInput");
  const useLlm = document.getElementById("useLlm").checked;
  const llmModel = document.getElementById("llmModel").value.trim() || "gpt-5.2";
  const maxRows = document.getElementById("maxRows").value;

  if (!fileInput.files.length) {
    setMessage("Please select a file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("use_llm", String(useLlm));
  formData.append("llm_model", llmModel);
  formData.append("max_rows_per_sheet", String(maxRows || 0));

  setMessage("Validating... this may take a moment.", "info");

  try {
    const response = await fetch(`${resolvedApiBase}/validate`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "Validation failed.");
    }

    const data = await response.json();
    lastCsv = data.report_csv || "";
    lastSummaryJson = data.summary_json || "";
    renderSummary(data.summary);
    renderReportRows(data.report || []);
    resultsSection.classList.remove("hidden");
    setMessage("Validation complete.", "success");
  } catch (error) {
    setMessage(error.message || "Something went wrong.", "error");
  }
});

hydrateApiBase();
