const uploadForm = document.getElementById("uploadForm");
const messageEl = document.getElementById("message");
const resultsSection = document.getElementById("resultsSection");
const summaryEl = document.getElementById("summary");
const reportTableBody = document.querySelector("#reportTable tbody");
const downloadCsvBtn = document.getElementById("downloadCsv");
const downloadJsonBtn = document.getElementById("downloadJson");

let lastCsv = "";
let lastSummaryJson = "";

function setMessage(text, type = "info") {
  messageEl.textContent = text;
  messageEl.className = `message ${type}`;
}

function clearMessage() {
  messageEl.textContent = "";
  messageEl.className = "message hidden";
}

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

  const fileInput = document.getElementById("fileInput");
  const resolvedApiBase = window.location.origin !== "null" ? window.location.origin : "";

  if (!fileInput.files.length) {
    setMessage("Please select a file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("use_llm", "true");

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
