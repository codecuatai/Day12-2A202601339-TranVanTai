// API key chỉ tồn tại trong bộ nhớ của tab, không được hard-code hoặc lưu vào repo.
const state = {
  busy: false,
  apiKey: "",
};

const elements = {
  apiKey: document.querySelector("#api-key"),
  userId: document.querySelector("#user-id"),
  form: document.querySelector("#chat-form"),
  question: document.querySelector("#question"),
  messages: document.querySelector("#messages"),
  send: document.querySelector("#send-button"),
  loadHistory: document.querySelector("#load-history"),
  status: document.querySelector("#status-badge"),
  usage: document.querySelector("#usage"),
};

function setStatus(label, kind = "") {
  elements.status.textContent = label;
  elements.status.className = `status-badge ${kind}`;
}

function addMessage(role, content) {
  const empty = elements.messages.querySelector(".empty-state");
  if (empty) empty.remove();

  // textContent chống XSS: câu trả lời được hiển thị như text, không chạy HTML.
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "Bạn" : "Agent";

  const body = document.createElement("div");
  body.textContent = content;
  message.append(label, body);
  elements.messages.appendChild(message);
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function showError(message) {
  const error = document.createElement("article");
  error.className = "message error-message";
  error.textContent = message;
  elements.messages.appendChild(error);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  setStatus("Có lỗi", "error");
}

function readCredentials() {
  state.apiKey = elements.apiKey.value.trim();
  const userId = elements.userId.value.trim();
  if (!state.apiKey) throw new Error("Vui lòng nhập API key.");
  if (!userId) throw new Error("Vui lòng nhập User ID.");
  return { apiKey: state.apiKey, userId };
}

function explainHttpError(status) {
  if (status === 401) return "API key không đúng hoặc đã bị thiếu.";
  if (status === 402) return "User đã vượt ngân sách tháng.";
  if (status === 429) return "Bạn đang gửi quá nhanh. Hãy thử lại sau.";
  if (status === 503) return "Service chưa sẵn sàng hoặc Redis đang lỗi.";
  return `Request thất bại với mã HTTP ${status}.`;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(explainHttpError(response.status)), { status: response.status });
  return data;
}

async function loadHistory() {
  try {
    const { apiKey, userId } = readCredentials();
    setStatus("Đang tải...", "");
    const data = await requestJson("/api/history", {
      headers: { "X-API-Key": apiKey, "X-User-Id": userId },
    });

    elements.messages.replaceChildren();
    if (!data.messages.length) {
      elements.messages.innerHTML = '<div class="empty-state">Chưa có lịch sử trò chuyện.</div>';
    } else {
      data.messages.forEach((message) => addMessage(message.role, message.content));
    }
    setStatus("Đã kết nối", "success");
  } catch (error) {
    showError(error.message);
  }
}

async function sendQuestion(event) {
  event.preventDefault();
  if (state.busy) return;

  const question = elements.question.value.trim();
  if (!question) return;

  try {
    const { apiKey, userId } = readCredentials();
    state.busy = true;
    elements.send.disabled = true;
    addMessage("user", question);
    elements.question.value = "";
    setStatus("Đang xử lý...", "");

    const data = await requestJson("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
        "X-User-Id": userId,
      },
      body: JSON.stringify({ question }),
    });

    addMessage("assistant", data.answer);
    elements.usage.textContent = `History: ${data.history_length} · Cost: $${data.cost_usd}`;
    setStatus("Đã kết nối", "success");
  } catch (error) {
    showError(error.message);
  } finally {
    state.busy = false;
    elements.send.disabled = false;
    elements.question.focus();
  }
}

// Enter gửi tin nhắn; Shift+Enter vẫn cho phép xuống dòng trong textarea.
elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

elements.form.addEventListener("submit", sendQuestion);
elements.loadHistory.addEventListener("click", loadHistory);
