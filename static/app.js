"use strict";
const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const submit = document.getElementById("submit");
const status = document.getElementById("status");
const result = document.getElementById("result");
const answer = document.getElementById("answer");
const matched = document.getElementById("matched-section");
const sources = document.getElementById("sources");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submit.disabled) return;
  result.hidden = true;
  answer.textContent = "";
  matched.textContent = "";
  sources.replaceChildren();
  const query = queryInput.value.trim();
  if (!query) {
    status.textContent = "Enter a demo issue before searching.";
    status.dataset.state = "error";
    queryInput.focus();
    return;
  }
  submit.disabled = true;
  form.setAttribute("aria-busy", "true");
  status.dataset.state = "loading";
  status.textContent = "Searching the local knowledge base…";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`/ask?${new URLSearchParams({q: query})}`, {
      signal: controller.signal, cache: "no-store",
    });
    if (!response.ok) throw new Error("Request failed");
    const data = await response.json();
    if (typeof data.answer !== "string" || !Array.isArray(data.sources)) {
      throw new Error("Invalid response");
    }
    if (!data.sources.length) {
      status.dataset.state = "empty";
      status.textContent = "No matching knowledge base entries. Try an English example; this does not mean your issue has no solution.";
      return;
    }
    matched.textContent = data.matched_section;
    answer.textContent = data.answer;
    for (const source of data.sources) {
      const item = document.createElement("li");
      item.textContent = `${source.section} · ${source.file} · score ${source.score}`;
      sources.append(item);
    }
    result.hidden = false;
    status.dataset.state = "success";
    status.textContent = "Retrieved a synthetic source excerpt. Check the source before using it.";
  } catch (error) {
    status.dataset.state = "error";
    status.textContent = error.name === "AbortError"
      ? "Search timed out. Please try again."
      : "Could not load an answer. Check the local server and try again.";
  } finally {
    clearTimeout(timeout);
    submit.disabled = false;
    form.setAttribute("aria-busy", "false");
  }
});
