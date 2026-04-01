const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASE = isLocalHost
  ? "http://127.0.0.1:8008"
  : "https://code-reusability-backend.vercel.app";
const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const messagesEl = document.getElementById("messages");
const sendBtn = document.getElementById("sendBtn");
const promptEl = document.getElementById("prompt");
const projectNameEl = document.getElementById("projectName");
const phaseBadgeEl = document.getElementById("phaseBadge");
const downloadBtnEl = document.getElementById("downloadBtn");
const deleteProjectsBtnEl = document.getElementById("deleteProjectsBtn");

function setDownloadLink(url = "", enabled = false) {
  if (!enabled || !url) {
    downloadBtnEl.href = "#";
    downloadBtnEl.classList.add("disabled");
    downloadBtnEl.setAttribute("aria-disabled", "true");
    return;
  }
  downloadBtnEl.href = url;
  downloadBtnEl.classList.remove("disabled");
  downloadBtnEl.setAttribute("aria-disabled", "false");
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

async function streamGenerate() {
  const message = promptEl.value.trim();
  const project_name = projectNameEl.value.trim();

  if (!project_name) {
    addMessage("error", "Project name is required.");
    return;
  }

  setDownloadLink();

  sendBtn.disabled = true;
  if (message) {
    addMessage("status", message, false, "user");
  }
  promptEl.value = "";

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
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
          if (event.type === "phase") {
            setPhase(event.phase);
          } else if (event.type === "success") {
            const url = `${API_BASE}${event.download_url}`;
            setDownloadLink(url, true);
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
          addMessage("status", payload, false, "assistant");
        }
      }
    }
  } catch (err) {
    addMessage("error", `Network error: ${err.message}`, false, "assistant");
  } finally {
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
    const res = await fetch(`${API_BASE}/api/projects`, { method: "DELETE" });
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

    setDownloadLink();
    const deletedCount = Number(payload?.deleted || 0);
    addMessage("success", `Deleted ${deletedCount} item(s) from projects folder.`, false, "assistant");
  } catch (err) {
    addMessage("error", `Network error: ${err.message}`, false, "assistant");
  } finally {
    deleteProjectsBtnEl.disabled = false;
  }
}

sendBtn.addEventListener("click", streamGenerate);
deleteProjectsBtnEl.addEventListener("click", deleteProjectFiles);
promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    streamGenerate();
  }
});

addMessage("status", "Start by sending any message. I will ask two requirement questions first.", false, "assistant");
setPhase("gather");
setDownloadLink();
