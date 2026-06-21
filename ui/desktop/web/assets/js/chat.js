
const chatForm = document.querySelector('#chat-form');
const chatInput = document.querySelector('#chat-input');
const chatMessages = document.querySelector('.message-area');
const quickPrompts = document.querySelectorAll('.prompt-chip');
const statusBadge = document.querySelector('#chat-status');

function createBubble(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '🧑' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    if (role === 'assistant') {
        wrapper.appendChild(avatar);
        wrapper.appendChild(bubble);
    } else {
        wrapper.appendChild(bubble);
        wrapper.appendChild(avatar);
    }

    return wrapper;
}

function appendMessage(role, text) {
    const bubble = createBubble(role, text);
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setStatus(text) {
    if (statusBadge) {
        statusBadge.textContent = text;
    }
}

function sendChatMessage(text) {
    if (!text.trim()) {
        return;
    }

    appendMessage('user', text);
    setStatus('Sending request...');
    chatInput.value = '';
    chatInput.focus();

    if (window.NativeBridge) {
        window.NativeBridge.send('chatMessage', { text });
    }
}

chatForm?.addEventListener('submit', function(event) {
    event.preventDefault();
    sendChatMessage(chatInput.value);
});

quickPrompts.forEach((chip) => {
    chip.addEventListener('click', () => {
        chatInput.value = chip.dataset.prompt;
        chatInput.focus();
    });
});

if (window.NativeBridge) {
    window.NativeBridge.receive((message) => {
        if (!message || !message.event) {
            return;
        }

        if (message.event === 'chatResponse') {
            appendMessage('assistant', message.payload?.text || 'Sorry, no response was returned.');
            setStatus('Answer received');
        }

        if (message.event === 'analysisUpdate') {
            setStatus('Analysis available');
        }
    });
}
