// Redirect straight to the dashboard if already signed in.
if (getToken()) {
  window.location.href = "dashboard.html";
}

document.querySelectorAll(".tab").forEach((tabBtn) => {
  tabBtn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    tabBtn.classList.add("active");
    document.getElementById(`${tabBtn.dataset.tab}-form`).classList.add("active");
  });
});

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("login-error");
  errorEl.textContent = "";
  try {
    const data = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("login-email").value.trim(),
        password: document.getElementById("login-password").value,
      }),
    });
    setSession(data.token, data.user);
    window.location.href = "dashboard.html";
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("register-error");
  errorEl.textContent = "";
  try {
    const data = await apiFetch("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        full_name: document.getElementById("reg-name").value.trim(),
        email: document.getElementById("reg-email").value.trim(),
        role: document.getElementById("reg-role").value,
        password: document.getElementById("reg-password").value,
      }),
    });
    setSession(data.token, data.user);
    window.location.href = "dashboard.html";
  } catch (err) {
    errorEl.textContent = err.message;
  }
});
