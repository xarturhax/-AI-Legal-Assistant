"use strict";
document.documentElement.classList.add("js-enabled");

// Desktop-навигация использует native details и работает без JavaScript.
const sectionMenu = document.querySelector(".c-sections");
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sectionMenu?.open) {
    sectionMenu.open = false;
    sectionMenu.querySelector("summary").focus();
  }
});
document.addEventListener("click", (event) => {
  if (sectionMenu?.open && !sectionMenu.contains(event.target)) sectionMenu.open = false;
});

// Обычная отправка во Flask сохраняется. Поля и submitter name/value не отключаются.
document.querySelectorAll("[data-loading-form]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "true";
    form.classList.add("is-loading");
    form.setAttribute("aria-busy", "true");
    form.querySelector(".loading-status").hidden = false;
    const button = event.submitter || form.querySelector("button");
    button?.setAttribute("aria-disabled", "true");
  });
});
window.addEventListener("pageshow", () => {
  document.querySelectorAll("[data-loading-form]").forEach((form) => {
    delete form.dataset.submitting;
    form.classList.remove("is-loading");
    form.removeAttribute("aria-busy");
    form.querySelector(".loading-status").hidden = true;
    form.querySelectorAll("[aria-disabled]").forEach((button) => button.removeAttribute("aria-disabled"));
  });
});

// CSRF остаётся обязательным и для JSON-запросов из собственных страниц.
window.localApi = async function (url, method = "GET", body) {
  const headers = {"X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || "Не удалось выполнить запрос.");
  return result;
};
