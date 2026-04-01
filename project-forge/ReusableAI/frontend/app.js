const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASES = isLocalHost
  ? ["http://127.0.0.1:8008"]
  : [
      "https://retrorsely-uncondensational-bentlee.ngrok-free.dev",
      "https://code-reusability-backend.vercel.app",
    ];
const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const messagesEl = document.getElementById("messages");
const sendBtn = document.getElementById("sendBtn");
const promptEl = document.getElementById("prompt");
const projectNameEl = document.getElementById("projectName");
const phaseBadgeEl = document.getElementById("phaseBadge");
const sampleTaskBtnEl = document.getElementById("sampleTaskBtn");
const clearChatBtnEl = document.getElementById("clearChatBtn");
const deleteProjectsBtnEl = document.getElementById("deleteProjectsBtn");

const sampleTasks = [
  "Create a FastAPI backend with connection to Google BigQuery and structured logging.",
  "Build a Flask API with PostgreSQL, JWT auth, Docker, and health/readiness endpoints.",
  "Generate a FastAPI + React starter with Redis caching, background jobs, and CI config.",
  "Create a LangChain RAG service with ingestion pipeline, vector store setup, and API routes.",
];
let sampleTaskIndex = 0;
let loadingOverlayEl = null;

async function fetchWithFallback(path, init) {
  let lastError = null;
  for (const base of API_BASES) {
    try {
      const response = await fetch(`${base}${path}`, init);
      return { response, base };
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error("No backend endpoint is reachable.");
}

function setPhase(phase) {
  const normalized = (phase || "gather").toLowerCase();
  const labels = {
    gather: "Gather",
    preview: "Preview",
    generate: "Generate",
    done: "Done",
  };
  const safe = labels[normalized] ? normalized : "gather";
  phaseBadgeEl.className = `phase-badge phase-${safe}`;
  phaseBadgeEl.textContent = labels[safe];
}

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderAssistantContent(text) {
  const marker = "Key decisions:";
  const markerIndex = text.indexOf(marker);
  const hasTree = markerIndex > 0 && text.includes("/") && text.includes("└──");

  if (!hasTree) {
    return `<div>${escapeHtml(text).replaceAll("\n", "<br/>")}</div>`;
  }

  const treePart = text.slice(0, markerIndex).trimEnd();
  const rest = text.slice(markerIndex).trimStart();
  return `
    <div>${escapeHtml(rest).replaceAll("\n", "<br/>")}</div>
    <pre class="assistant-pre">${escapeHtml(treePart)}</pre>
  `;
}

function addMessage(type, text, html = false, role = "assistant") {
  const el = document.createElement("div");
  el.className = `msg ${type} ${role}`;
  if (html) {
    el.innerHTML = text;
  } else {
    el.textContent = text;
  }
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showLoadingOverlay(message = "Generating response...") {
  hideLoadingOverlay();
  const el = document.createElement("div");
  el.className = "loading-overlay";
  el.innerHTML = `
    <div class="loading-card" role="status" aria-live="polite">
      <span class="loading-spinner" aria-hidden="true"></span>
      <span class="loading-text">${escapeHtml(message)}</span>
    </div>
  `;
  messagesEl.appendChild(el);
  loadingOverlayEl = el;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideLoadingOverlay() {
  if (!loadingOverlayEl) {
    return;
  }
  loadingOverlayEl.remove();
  loadingOverlayEl = null;
}

async function streamGenerate() {
  const message = promptEl.value.trim();
  const project_name = projectNameEl.value.trim();

  if (!project_name) {
    addMessage("error", "Project name is required.");
    return;
  }

  sendBtn.disabled = true;
  showLoadingOverlay("Waiting for API response...");
  if (message) {
    addMessage("status", message, false, "user");
  }
  promptEl.value = "";

  try {
    const { response: res, base: apiBase } = await fetchWithFallback("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, project_name, session_id: sessionId }),
    });

    if (!res.ok || !res.body) {
      addMessage("error", `Request failed: ${res.status}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        if (!chunk.startsWith("data:")) continue;
        const payload = chunk.slice(5).trim();
        if (!payload) continue;

        try {
          const event = JSON.parse(payload);
          hideLoadingOverlay();
          if (event.type === "phase") {
            setPhase(event.phase);
          } else if (event.type === "success") {
            const url = `${apiBase}${event.download_url}`;
            addMessage(
              "success",
              `${event.message}<br/><a href=\"${url}\" target=\"_blank\">Download zip</a>`,
              true,
              "assistant"
            );
            setPhase("done");
          } else if (event.type === "assistant") {
            addMessage("reasoning", renderAssistantContent(event.message || payload), true, "assistant");
          } else {
            addMessage(event.type || "status", event.message || payload, false, "assistant");
          }
        } catch {
          hideLoadingOverlay();
          addMessage("status", payload, false, "assistant");
        }
      }
    }
  } catch (err) {
    hideLoadingOverlay();
    addMessage("error", `Network error: ${err.message}`, false, "assistant");
  } finally {
    hideLoadingOverlay();
    sendBtn.disabled = false;
  }
}

async function deleteProjectFiles() {
  const approved = window.confirm("Delete all files in the projects folder?");
  if (!approved) {
    return;
  }

  deleteProjectsBtnEl.disabled = true;
  try {
    const { response: res } = await fetchWithFallback("/api/projects", { method: "DELETE" });
    let payload = null;
    try {
      payload = await res.json();
    } catch {
      payload = null;
    }

    if (!res.ok) {
      const errorMessage = payload?.error || `Delete failed: ${res.status}`;
      addMessage("error", errorMessage, false, "assistant");
      return;
    }

    const deletedCount = Number(payload?.deleted || 0);
    addMessage("success", `Deleted ${deletedCount} item(s) from projects folder.`, false, "assistant");
  } catch (err) {
    addMessage("error", `Network error: ${err.message}`, false, "assistant");
  } finally {
    deleteProjectsBtnEl.disabled = false;
  }
}

function clearChat() {
  messagesEl.innerHTML = "";
  promptEl.value = "";
  setPhase("gather");
  addMessage("status", "Chat cleared. Start by sending any message.", false, "assistant");
}

function insertSampleTask() {
  promptEl.value = sampleTasks[sampleTaskIndex];
  sampleTaskIndex = (sampleTaskIndex + 1) % sampleTasks.length;
  promptEl.focus();
}

sendBtn.addEventListener("click", streamGenerate);
sampleTaskBtnEl.addEventListener("click", insertSampleTask);
clearChatBtnEl.addEventListener("click", clearChat);
deleteProjectsBtnEl.addEventListener("click", deleteProjectFiles);
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    streamGenerate();
  }
});

addMessage("status", "Start by sending any message. I will ask two requirement questions first.", false, "assistant");
setPhase("gather");
