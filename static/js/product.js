let priceChart = null;

document.addEventListener("DOMContentLoaded", () => {
    loadForecast();
    document.getElementById("retrain-btn").addEventListener("click", retrain);
});

async function loadForecast() {
    showLoading("Loading forecast...");
    hideError();

    try {
        const res = await fetch(`/api/products/${PRODUCT_ID}/forecast/`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Failed to load (${res.status})`);
        }
        const data = await res.json();
        renderProduct(data);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

function renderProduct(data) {
    document.getElementById("product-name").textContent = data.product_name;
    document.getElementById("product-content").classList.remove("hidden");

    if (data.forecast.next_dip_date) {
        document.getElementById("dip-date").textContent = formatDate(data.forecast.next_dip_date);
        document.getElementById("dip-price").textContent = `$${data.forecast.next_dip_price}`;
        document.getElementById("dip-alert").classList.remove("hidden");
    } else {
        document.getElementById("no-dip").classList.remove("hidden");
    }

    renderChart(data.price_history, data.forecast);
    renderComparison(data.model_comparison, data.best_model);
}

function renderChart(history, forecast) {
    const ctx = document.getElementById("price-chart").getContext("2d");

    const historyDates = history.map((p) => p.date);
    const historyPrices = history.map((p) => p.price);
    const forecastDates = forecast.forecast_dates;
    const forecastPrices = forecast.forecast_prices;

    const allDates = [...historyDates, ...forecastDates];
    const historyData = [...historyPrices, ...Array(forecastDates.length).fill(null)];
    const forecastData = [
        ...Array(historyDates.length - 1).fill(null),
        historyPrices[historyPrices.length - 1],
        ...forecastPrices,
    ];

    if (priceChart) priceChart.destroy();

    priceChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: allDates.map(formatDate),
            datasets: [
                {
                    label: "Price History",
                    data: historyData,
                    borderColor: "#60a5fa",
                    backgroundColor: "rgba(96, 165, 250, 0.1)",
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: true,
                },
                {
                    label: `Forecast (${forecast.model_type.toUpperCase()})`,
                    data: forecastData,
                    borderColor: "#ff9900",
                    borderWidth: 2,
                    borderDash: [6, 4],
                    pointRadius: 0,
                    tension: 0.3,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { labels: { color: "#e8eaed" } },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            if (ctx.parsed.y === null) return null;
                            return `${ctx.dataset.label}: $${ctx.parsed.y.toFixed(2)}`;
                        },
                    },
                },
            },
            scales: {
                x: {
                    ticks: { color: "#9aa0b4", maxTicksLimit: 12 },
                    grid: { color: "#2e3348" },
                },
                y: {
                    ticks: {
                        color: "#9aa0b4",
                        callback: (v) => `$${v}`,
                    },
                    grid: { color: "#2e3348" },
                },
            },
        },
    });
}

function renderComparison(models, bestType) {
    const tbody = document.querySelector("#comparison-table tbody");
    tbody.innerHTML = "";

    const sorted = [...models].sort((a, b) => a.mae - b.mae);
    sorted.forEach((m) => {
        const tr = document.createElement("tr");
        const isBest = m.model_type === bestType;
        tr.innerHTML = `
            <td>${m.model_type.toUpperCase()}</td>
            <td>${m.mae.toFixed(2)}</td>
            <td>${m.mape.toFixed(1)}</td>
            <td>${m.rmse.toFixed(2)}</td>
            <td>${isBest ? '<span class="badge-best">BEST</span>' : ""}</td>
        `;
        tbody.appendChild(tr);
    });
}

async function retrain() {
    const btn = document.getElementById("retrain-btn");
    btn.disabled = true;
    btn.textContent = "Retraining...";
    showLoading("Retraining all models...");
    document.getElementById("product-content").classList.add("hidden");

    try {
        const res = await fetch(`/api/products/${PRODUCT_ID}/retrain/`, { method: "POST" });
        const data = await res.json();
        await pollJob(data.job_id);
        await loadForecast();
    } catch (err) {
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Retrain Models";
    }
}

async function pollJob(jobId) {
    for (let i = 0; i < 120; i++) {
        const res = await fetch(`/api/jobs/${jobId}/`);
        const data = await res.json();
        if (data.status === "complete") return;
        if (data.status === "failed") throw new Error(data.error_message || "Training failed");
        document.getElementById("loading-text").textContent =
            data.status === "training" ? "Training models..." : "Fetching price history...";
        await sleep(2000);
    }
    throw new Error("Training timed out");
}

function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function showLoading(text) {
    document.getElementById("loading-text").textContent = text;
    document.getElementById("loading").classList.remove("hidden");
}

function hideLoading() {
    document.getElementById("loading").classList.add("hidden");
}

function showError(msg) {
    const el = document.getElementById("error");
    el.textContent = msg;
    el.classList.remove("hidden");
}

function hideError() {
    document.getElementById("error").classList.add("hidden");
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
