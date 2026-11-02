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

const scenarioValueRequests = new WeakMap();

async function updateScenarioPointValue(pointSelect, showLoading = true) {
    const form = pointSelect.closest("form");
    const readout = form.querySelector("[data-scenario-current-value]");
    const deviceId = form.querySelector("[data-scenario-device]").value;
    const pointName = pointSelect.value;
    scenarioValueRequests.get(pointSelect)?.abort();
    if (!deviceId || !pointName || pointSelect.disabled) {
        readout.textContent = "Current value: unavailable";
        return;
    }
    const controller = new AbortController();
    scenarioValueRequests.set(pointSelect, controller);
    if (showLoading) readout.textContent = "Current value: loading...";
    try {
        const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}`, {
            signal: controller.signal,
            cache: "no-store"
        });
        if (!response.ok) throw new Error("Device unavailable");
        const device = await response.json();
        const point = device.points.find((point) => point.object_name === pointName);
        if (!point || device.status !== "online") throw new Error("Point unavailable");
        if (controller.signal.aborted || !pointSelect.isConnected) return;
        const units = {
            degreesCelsius: "\u00b0C",
            degreesFahrenheit: "\u00b0F",
            partsPerMillion: "ppm",
            percent: "%",
            percentRelativeHumidity: "% RH",
            noUnits: ""
        };
        const unit = units[point.units] ?? point.units;
        const value = typeof point.present_value === "number"
            ? new Intl.NumberFormat(undefined, {maximumSignificantDigits: 8}).format(point.present_value)
            : String(point.present_value);
        readout.textContent = `Current value: ${value}${unit ? ` ${unit}` : ""}`;
    } catch (error) {
        if (!controller.signal.aborted && pointSelect.isConnected) {
            readout.textContent = "Current value: unavailable";
        }
    }
}

function updateScenarioPoints(deviceSelect) {
    const form = deviceSelect.closest("form");
    const pointSelect = form.querySelector("select[data-scenario-point]");
    if (!pointSelect) return;

    const availableOptions = [...pointSelect.options].filter((option) => option.dataset.deviceId);
    const matchingOptions = availableOptions.filter((option) => option.dataset.deviceId === deviceSelect.value);
    for (const option of availableOptions) option.hidden = option.dataset.deviceId !== deviceSelect.value;
    if (pointSelect.selectedOptions[0]?.hidden) pointSelect.value = matchingOptions[0]?.value || "";
    pointSelect.disabled = matchingOptions.length === 0;
    updateScenarioPointValue(pointSelect);
}

document.addEventListener("change", (event) => {
    if (event.target.matches("select[data-scenario-device]")) {
        event.target.closest("form").dataset.dirty = "true";
        updateScenarioPoints(event.target);
    } else if (event.target.matches("select[data-scenario-point]")) {
        event.target.closest("form").dataset.dirty = "true";
        updateScenarioPointValue(event.target);
    }
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("select[data-scenario-device]").forEach(updateScenarioPoints);
});
document.addEventListener("htmx:afterSwap", (event) => {
    event.detail.target.querySelectorAll("select[data-scenario-device]").forEach(updateScenarioPoints);
});

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
        event.detail.target.querySelectorAll("select[data-scenario-point]").forEach((pointSelect) => {
            updateScenarioPointValue(pointSelect, false);
        });
    }
});
document.addEventListener("htmx:responseError", () => notify("Refresh failed. Check server health.", true));
