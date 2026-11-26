"use strict";

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
    form.setAttribute("aria-busy", "true");
    form.querySelector(".loading-status").hidden = false;
    const button = event.submitter || form.querySelector("button");
    button?.setAttribute("aria-disabled", "true");
  });
});
window.addEventListener("pageshow", () => {
  document.querySelectorAll("[data-loading-form]").forEach((form) => {
    delete form.dataset.submitting;
    form.removeAttribute("aria-busy");
    form.querySelector(".loading-status").hidden = true;
    form.querySelectorAll("[aria-disabled]").forEach((button) => button.removeAttribute("aria-disabled"));
  });
});
