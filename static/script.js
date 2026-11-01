/*
Smart Flight Booking with Agentic AI
Author: Abdul : Full Stack - AI Engineer
Production frontend controller.
*/
let currentThreadId = localStorage.getItem("smart_flight_thread_id") || null;
let latestAnswerMarkdown = "";
let progressTimer = null;

const $ = (id) => document.getElementById(id);

function setPrompt(text) {
    $("userInput").value = text;
    updateCharCount();
    $("userInput").focus();
}

function updateCharCount() {
    $("charCount").textContent = `${$("userInput").value.length} / 4000`;
}

function setLoading(isLoading) {
    $("sendBtn").disabled = isLoading;
    $("btnText").classList.toggle("hidden", isLoading);
    $("btnLoader").classList.toggle("hidden", !isLoading);
}

function showError(message) {
    $("errorBox").textContent = message;
    $("errorBox").classList.remove("hidden");
}

function hideError() {
    $("errorBox").classList.add("hidden");
    $("errorBox").textContent = "";
}

function updateProgress(step, text, width) {
    $("progressSection").classList.remove("hidden");
    $("progressText").textContent = text;
    $("progressBar").style.width = `${width}%`;
    ["flight", "hotel", "itinerary", "final"].forEach((name) => {
        $(`step-${name}`).classList.toggle("active", name === step);
    });
}

function startProgress() {
    const steps = [
        ["flight", "Searching flight intelligence…", 25],
        ["hotel", "Researching hotels and destination options…", 50],
        ["itinerary", "Building your day-by-day itinerary…", 75],
        ["final", "Preparing your booking advisor brief…", 92]
    ];
    let index = 0;
    updateProgress(...steps[0]);
    progressTimer = setInterval(() => {
        index = Math.min(index + 1, steps.length - 1);
        updateProgress(...steps[index]);
    }, 1800);
}

function stopProgress() {
    if (progressTimer) clearInterval(progressTimer);
    progressTimer = null;
    updateProgress("final", "Plan ready", 100);
    setTimeout(() => $("progressSection").classList.add("hidden"), 900);
}

function showResult(answer, threadId) {
    latestAnswerMarkdown = answer || "";
    const resultBox = $("resultBox");

    if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
        const rendered = marked.parse(latestAnswerMarkdown, { breaks: true, gfm: true });
        resultBox.innerHTML = DOMPurify.sanitize(rendered);
    } else {
        resultBox.textContent = latestAnswerMarkdown;
    }

    $("threadInfo").textContent = `Conversation ID: ${threadId}`;
    $("resultSection").classList.remove("hidden");
    $("resultSection").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function sendMessage() {
    hideError();
    const message = $("userInput").value.trim();

    if (message.length < 2) {
        showError("Please describe your destination, dates or travel requirements.");
        $("userInput").focus();
        return;
    }

    setLoading(true);
    startProgress();

    try {
        const response = await fetch("/api/travel", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ message, thread_id: currentThreadId })
        });

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error(`Server returned an invalid response (${response.status}).`);
        }

        if (!response.ok || !data.success) {
            throw new Error(data.error || "The booking workflow could not be completed.");
        }

        currentThreadId = data.thread_id;
        localStorage.setItem("smart_flight_thread_id", currentThreadId);
        showResult(data.answer, currentThreadId);
    } catch (error) {
        showError(error.message || "Something went wrong. Please try again.");
    } finally {
        stopProgress();
        setLoading(false);
    }
}

function newConversation() {
    currentThreadId = null;
    latestAnswerMarkdown = "";
    localStorage.removeItem("smart_flight_thread_id");
    $("userInput").value = "";
    updateCharCount();
    $("resultSection").classList.add("hidden");
    $("progressSection").classList.add("hidden");
    hideError();
    $("userInput").focus();
}

async function copyResult() {
    const text = $("resultBox").innerText.trim();
    if (!text) return;

    try {
        await navigator.clipboard.writeText(text);
        const button = document.querySelector(".copy-btn");
        const oldText = button.textContent;
        button.textContent = "Copied ✓";
        setTimeout(() => button.textContent = oldText, 1400);
    } catch {
        showError("Could not copy the travel plan. Please select the text manually.");
    }
}

function downloadPDF() {
    const pdfContent = $("pdfContent");
    if (!latestAnswerMarkdown || !pdfContent || typeof html2pdf === "undefined") {
        showError("No travel plan is available to export.");
        return;
    }

    const button = document.querySelector(".download-btn");
    const oldText = button.textContent;
    button.textContent = "Preparing…";
    button.disabled = true;

    html2pdf().set({
        margin: 0.45,
        filename: "smart-flight-booking-plan.pdf",
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: "#ffffff" },
        jsPDF: { unit: "in", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["avoid-all", "css", "legacy"] }
    }).from(pdfContent).save()
      .catch(() => showError("Could not export the PDF."))
      .finally(() => {
          button.textContent = oldText;
          button.disabled = false;
      });
}

document.addEventListener("DOMContentLoaded", () => {
    updateCharCount();
    $("userInput").addEventListener("input", updateCharCount);
    $("userInput").addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
});
