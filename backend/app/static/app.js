"use strict";
// CSRF остаётся обязательным и для JSON-запросов из собственных страниц.
window.localApi = async function (url, method = "GET", body) {
  const headers = {"X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || "Не удалось выполнить запрос.");
  return result;
};
