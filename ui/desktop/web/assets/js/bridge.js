
window.NativeBridge = {
    _handler: null,
    send(event, payload) {
        const message = { event, payload };

        if (window.qt && typeof window.qt.postMessage === 'function') {
            window.qt.postMessage(JSON.stringify(message));
            return;
        }

        if (window.chrome && window.chrome.webview && typeof window.chrome.webview.postMessage === 'function') {
            window.chrome.webview.postMessage(message);
            return;
        }

        console.debug('Native bridge not available:', message);
    },
    receive(handler) {
        this._handler = handler;
    }
};

window.receiveNativeMessage = function(message) {
    if (window.NativeBridge._handler) {
        window.NativeBridge._handler(message);
    }
};

window.addEventListener('DOMContentLoaded', () => {
    document.body.classList.remove('no-js');
});
