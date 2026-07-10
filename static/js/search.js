const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const loading = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const errorEl = document.getElementById("error");
const resultsSection = document.getElementById("results");
const resultsList = document.getElementById("results-list");

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;

    showLoading("Searching...");
    hideError();
    resultsSection.classList.add("hidden");

    try {
        const res = await fetch("/api/search/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });
        if (!res.ok) throw new Error(`Search failed (${res.status})`);
        const data = await res.json();
        await handleResults(data.results);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
});

async function handleResults(results) {
    if (!results.length) {
        showError("No products found for that query.");
        return;
    }

    const pendingJobs = results.filter((r) => r.status === "processing");

    if (pendingJobs.length > 0) {
        showLoading(`Training models for ${pendingJobs.length} product(s)...`);
        await pollJobs(pendingJobs);
        hideLoading();
    }

    renderResults(results);
}

async function pollJobs(jobs) {
    const maxAttempts = 120;
    let attempts = 0;

    while (attempts < maxAttempts) {
        const statuses = await Promise.all(
            jobs.map(async (j) => {
                const res = await fetch(`/api/jobs/${j.job_id}/`);
                return res.json();
            })
        );

        const allDone = statuses.every(
            (s) => s.status === "complete" || s.status === "failed"
        );

        if (allDone) {
            jobs.forEach((j, i) => {
                j.status = statuses[i].status === "complete" ? "ready" : "failed";
            });
            return;
        }

        const training = statuses.filter((s) => s.status === "training").length;
        const fetching = statuses.filter((s) => s.status === "fetching").length;
        if (training > 0) {
            loadingText.textContent = `Training ${training} model(s)...`;
        } else if (fetching > 0) {
            loadingText.textContent = "Fetching price history...";
        }

        await sleep(2000);
        attempts++;
    }

    jobs.forEach((j) => {
        if (j.status === "processing") j.status = "timeout";
    });
}

function renderResults(results) {
    resultsList.innerHTML = "";
    results.forEach((r) => {
        const card = document.createElement("a");
        card.className = "result-card";
        card.href = r.status === "ready" ? `/product/${r.product_id}/` : "#";

        const statusClass =
            r.status === "ready" ? "ready" : r.status === "processing" ? "processing" : "";
        const statusLabel =
            r.status === "ready"
                ? "Ready"
                : r.status === "processing"
                ? "Processing..."
                : r.status === "failed"
                ? "Failed"
                : "Timed out";

        card.innerHTML = `
            <span>${r.name}</span>
            <span class="status ${statusClass}">${statusLabel}</span>
        `;
        resultsList.appendChild(card);
    });
    resultsSection.classList.remove("hidden");
}

function showLoading(text) {
    loadingText.textContent = text;
    loading.classList.remove("hidden");
}

function hideLoading() {
    loading.classList.add("hidden");
}

function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove("hidden");
}

function hideError() {
    errorEl.classList.add("hidden");
}

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
