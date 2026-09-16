/* Shared API client. Same origin as the backend when served via Flask's
   static route; override API_BASE if you host the frontend separately. */
const API_BASE = window.location.origin.includes("5000") || window.location.protocol === "file:"
  ? "http://localhost:5000"
  : "";

function getToken() {
  return localStorage.getItem("nms_token");
}

function setSession(token, user) {
  localStorage.setItem("nms_token", token);
  localStorage.setItem("nms_user", JSON.stringify(user));
}

function getUser() {
  const raw = localStorage.getItem("nms_user");
  return raw ? JSON.parse(raw) : null;
}

function clearSession() {
  localStorage.removeItem("nms_token");
  localStorage.removeItem("nms_user");
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearSession();
    window.location.href = "index.html";
    throw new Error("Session expired");
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}
