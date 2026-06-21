
const bars = document.querySelectorAll('.risk-bar span');

function animateBars() {
    bars.forEach((bar) => {
        const width = bar.dataset.value || 0;
        bar.style.width = `${width}%`;
    });
}

function updateMetric(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function updateResults(payload) {
    if (!payload) {
        return;
    }

    updateMetric('ed-value', payload.edScore ?? 'N/A');
    updateMetric('safety-label', payload.safetyLabel ?? 'Unknown');
    updateMetric('confidence-value', payload.confidenceLabel ?? 'N/A');

    document.querySelectorAll('.risk-bar span').forEach((bar) => {
        if (bar.dataset.key && payload[bar.dataset.key] !== undefined) {
            bar.style.width = `${payload[bar.dataset.key]}%`;
        }
    });
}

window.addEventListener('DOMContentLoaded', () => {
    setTimeout(animateBars, 120);
});

if (window.NativeBridge) {
    window.NativeBridge.receive((message) => {
        if (!message || message.event !== 'analysisUpdate') {
            return;
        }
        updateResults(message.payload);
    });
}
