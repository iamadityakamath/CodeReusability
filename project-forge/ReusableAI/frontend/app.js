const API_BASE = "http://127.0.0.1:8008";

const messagesEl = document.getElementById("messages");
const sendBtn = document.getElementById("sendBtn");
const promptEl = document.getElementById("prompt");
const projectNameEl = document.getElementById("projectName");

function addMessage(type, text, html = false) {
  const el = document.createElement("div");
  el.className = `msg ${type}`;
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

  if (!message || !project_name) {
    addMessage("error", "Project name and prompt are required.");
    return;
  }

  sendBtn.disabled = true;
  addMessage("status", `Starting generation for ${project_name}...`);

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, project_name }),
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
          if (event.type === "success") {
            const url = `${API_BASE}${event.download_url}`;
            addMessage(
              "success",
              `${event.message}<br/><a href=\"${url}\" target=\"_blank\">Download zip</a>`,
              true
            );
          } else {
            addMessage(event.type || "status", event.message || payload);
          }
        } catch {
          addMessage("status", payload);
        }
      }
    }
  } catch (err) {
    addMessage("error", `Network error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

sendBtn.addEventListener("click", streamGenerate);
