/* Presentation preferences only. Authentication is always enforced by Django. */
(() => {
  "use strict";
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  let savedTheme = null;
  try { savedTheme = localStorage.getItem("modern-secured-theme"); } catch { /* Storage may be disabled. */ }
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(theme === "dark"));
      button.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} theme`);
    });
  };
  applyTheme(savedTheme === "dark" || savedTheme === "light" ? savedTheme : (systemDark.matches ? "dark" : "light"));
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      savedTheme = root.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(savedTheme);
      try { localStorage.setItem("modern-secured-theme", savedTheme); } catch { /* Preference remains valid for this page. */ }
    });
  });
  systemDark.addEventListener("change", (event) => { if (!savedTheme) applyTheme(event.matches ? "dark" : "light"); });
  document.querySelectorAll('input[type="password"]').forEach((input) => {
    if (!input.id) return;
    input.dataset.password = "true";
    const wrapper = input.closest(".field-input") || input.parentElement;
    if (!wrapper || wrapper.querySelector(".password-toggle")) return;
    wrapper.classList.add("field-input");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle";
    button.textContent = "Show";
    button.setAttribute("aria-controls", input.id);
    button.setAttribute("aria-label", "Show password");
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", `${show ? "Hide" : "Show"} password`);
      button.setAttribute("aria-pressed", String(show));
    });
    wrapper.append(button);
  });
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (event.defaultPrevented) return;
      if (form.getAttribute("aria-busy") === "true") {
        event.preventDefault();
        return;
      }
      const button = event.submitter;
      if (!button || button.dataset.noLoading !== undefined) return;
      form.setAttribute("aria-busy", "true");
      // Preserve submitted button names/values; disabling would omit them from the request.
      button.dataset.originalLabel = button.textContent;
      button.textContent = button.dataset.loadingLabel || "Please wait…";
      button.setAttribute("aria-disabled", "true");
    });
  });
  window.addEventListener("pageshow", () => {
    document.querySelectorAll("form[aria-busy]").forEach((form) => form.removeAttribute("aria-busy"));
    document.querySelectorAll("[data-original-label]").forEach((button) => {
      button.textContent = button.dataset.originalLabel;
      button.removeAttribute("aria-disabled");
      delete button.dataset.originalLabel;
    });
  });
})();
