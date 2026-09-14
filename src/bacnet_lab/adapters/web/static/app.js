"use strict";

function notify(message, isError = false) {
    const box = document.getElementById("toast-container");
    box.textContent = message;
    box.className = "toast-container toast " + (isError ? "error" : "success");
    box.setAttribute("role", "status");
}

function readValue(input) {
    if (input.dataset.kind === "boolean") return input.value === "true";
    if (input.dataset.kind === "number") {
        if (!input.value.trim() || !Number.isFinite(Number(input.value))) {
            throw new Error("Enter a finite number.");
        }
        return Number(input.value);
    }
    return input.value;
}

document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-api]");
    if (!form) return;
    event.preventDefault();
    if (form.dataset.busy) return;
    form.dataset.busy = "true";
    form.setAttribute("aria-busy", "true");
    try {
        const values = {};
        for (const input of form.querySelectorAll("[name]")) values[input.name] = readValue(input);
        const body = form.dataset.scenario ? {params: values} : values;
        const response = await fetch(form.dataset.api, {
            method: form.dataset.method || "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });
        const result = response.status === 204 ? {} : await response.json();
        if (!response.ok) {
            const detail = result.detail;
            throw new Error(Array.isArray(detail) ? detail.map(e => e.msg).join("; ") : detail || "Request failed");
        }
        if (result.secret) {
            const secret = document.getElementById("created-secret");
            secret.hidden = false;
            secret.textContent = "Save this secret now; it will not be shown again: " + result.secret;
            htmx.trigger(document.body, "endpoints-changed");
        }
        if (form.dataset.method === "DELETE") htmx.trigger(document.body, "endpoints-changed");
        notify(Object.hasOwn(result, "present_value") ? "Effective value: " + result.present_value : "Done");
        form.dataset.dirty = "false";
    } catch (error) {
        notify(error.message, true);
    } finally {
        delete form.dataset.busy;
        form.removeAttribute("aria-busy");
    }
});

// Polling must not discard an edit, even after its field loses focus.
document.addEventListener("input", (event) => {
    const form = event.target.closest("form[data-api]");
    if (form) form.dataset.dirty = "true";
});
document.addEventListener("htmx:beforeSwap", (event) => {
    if (event.detail.target.querySelector('form[data-dirty="true"], form[data-busy="true"]')) {
        event.detail.shouldSwap = false;
    }
});
document.addEventListener("htmx:responseError", () => notify("Refresh failed. Check server health.", true));
