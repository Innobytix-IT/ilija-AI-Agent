// Offenes Leuchten v5.0 – Frontend Logic (Mobile-optimiert)

const chatContainer   = document.getElementById('chat-container');
const messageInput    = document.getElementById('message-input');
const sendBtn         = document.getElementById('send-btn');
const clearBtn        = document.getElementById('clear-btn');
const providerSelect  = document.getElementById('provider-select');
const typingIndicator = document.getElementById('typing-indicator');
const reloadStatus    = document.getElementById('reload-status');

let messageCount  = 0;
let pendingUpload = null;   // { type: 'audio'|'file', file: File }

// ── MediaRecorder State ────────────────────────────────────────
let mediaRecorder    = null;
let audioChunks      = [];
let recordingActive  = false;

// ── Init ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadProviders();
    updateStats();

    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 100) + 'px';
    });

    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            pendingUpload ? sendUpload() : sendMessage();
        }
    });

    sendBtn.addEventListener('click', () => {
        pendingUpload ? sendUpload() : sendMessage();
    });

    clearBtn.addEventListener('click', clearChat);

    providerSelect.addEventListener('change', (e) => {
        addSystemMessage(`Provider: ${e.target.options[e.target.selectedIndex].text}`);
    });
});

// ── Provider ───────────────────────────────────────────────────
async function loadProviders() {
    try {
        const res = await fetch('/api/providers');
        const providers = await res.json();
        providerSelect.innerHTML = '<option value="auto">Auto-Wahl</option>';
        for (const [key, p] of Object.entries(providers)) {
            if (p.available) {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = `${p.name}`;
                providerSelect.appendChild(opt);
            }
        }
    } catch (e) { console.error('Provider laden:', e); }
}

// ── Stats ──────────────────────────────────────────────────────
async function updateStats() {
    try {
        const res = await fetch('/api/stats');
        const stats = await res.json();
        document.getElementById('provider-status').textContent = `● ${stats.provider?.toUpperCase() || '–'}`;
        document.getElementById('skills-count').textContent    = `⬡ ${stats.skills || 0} Skills`;
        document.getElementById('message-count').textContent   = `↕ ${messageCount}`;
    } catch (e) {}
    setTimeout(updateStats, 5000);
}

// ── Skill Reload ───────────────────────────────────────────────
async function reloadSkills() {
    const btn = document.getElementById('reload-btn');
    btn.classList.add('spinning');
    reloadStatus.textContent = 'Lade…';
    reloadStatus.className = 'reload-status';
    try {
        const res = await fetch('/api/reload', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            reloadStatus.textContent = `✓ ${data.count} Skills`;
            reloadStatus.className = 'reload-status success';
            addSystemMessage(`Skills neu geladen – ${data.count} verfügbar`);
            updateStats();
        } else throw new Error(data.error);
    } catch (e) {
        reloadStatus.textContent = `✗ ${e.message}`;
        reloadStatus.className = 'reload-status error';
    } finally {
        btn.classList.remove('spinning');
        setTimeout(() => {
            reloadStatus.textContent = '';
            reloadStatus.className = 'reload-status';
        }, 4000);
    }
}

// ── Mikrofon – Live-Aufnahme ───────────────────────────────────
async function toggleRecording() {
    const micBtn = document.getElementById('mic-btn');

    // Kein sicherer Kontext (HTTP statt HTTPS) → Datei-Picker Fallback
    if (!navigator.mediaDevices || !window.isSecureContext) {
        let audioInput = document.getElementById('audio-fallback-input');
        if (!audioInput) {
            audioInput = document.createElement('input');
            audioInput.type = 'file';
            audioInput.id = 'audio-fallback-input';
            audioInput.accept = 'audio/*,.ogg,.mp3,.wav,.m4a,.webm';
            audioInput.style.display = 'none';
            audioInput.onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;
                pendingUpload = { type: 'audio', file };
                showUploadPreview(`🎙 ${file.name} (${(file.size/1024).toFixed(1)} KB)`);
                audioInput.value = '';
            };
            document.body.appendChild(audioInput);
        }
        audioInput.click();
        return;
    }

    if (recordingActive) {
        mediaRecorder.stop();
        return;
    }

    // Mikrofon-Erlaubnis anfragen
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        recordingActive = true;

        // Bestes Format wählen
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
                ? 'audio/ogg;codecs=opus'
                : 'audio/webm';

        mediaRecorder = new MediaRecorder(stream, { mimeType });

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            recordingActive = false;
            micBtn.classList.remove('recording');
            hideRecordingIndicator();

            // Stream schließen
            stream.getTracks().forEach(t => t.stop());

            if (audioChunks.length === 0) return;

            const blob = new Blob(audioChunks, { type: mimeType });
            const ext  = mimeType.includes('ogg') ? '.ogg' : '.webm';
            const file = new File([blob], `aufnahme${ext}`, { type: mimeType });

            pendingUpload = { type: 'audio', file };
            showUploadPreview(`🎙 Aufnahme (${(file.size / 1024).toFixed(1)} KB)`);
        };

        mediaRecorder.start();
        micBtn.classList.add('recording');
        showRecordingIndicator();

    } catch (e) {
        addErrorMessage(`Mikrofon nicht verfügbar: ${e.message}`);
    }
}

function showRecordingIndicator() {
    let ind = document.getElementById('recording-indicator');
    if (!ind) {
        ind = document.createElement('div');
        ind.id = 'recording-indicator';
        ind.className = 'recording-indicator';
        ind.innerHTML = `<span class="rec-dot"></span><span>Aufnahme läuft – nochmal tippen zum Stoppen</span>`;
        const inputArea = document.querySelector('.input-area');
        inputArea.parentNode.insertBefore(ind, inputArea);
    }
    ind.style.display = 'flex';
}

function hideRecordingIndicator() {
    const ind = document.getElementById('recording-indicator');
    if (ind) ind.style.display = 'none';
}

// ── Datei-Upload ───────────────────────────────────────────────
function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    pendingUpload = { type: 'file', file };
    showUploadPreview(`📎 ${file.name} (${(file.size / 1024).toFixed(1)} KB)`);
    input.value = '';
}

function showUploadPreview(text) {
    const preview = document.getElementById('upload-preview');
    document.getElementById('upload-preview-name').textContent = text;
    preview.style.display = 'flex';
    messageInput.placeholder = 'Optionale Frage zur Datei…';
    messageInput.focus();
}

function cancelUpload() {
    pendingUpload = null;
    document.getElementById('upload-preview').style.display = 'none';
    messageInput.placeholder = 'Nachricht eingeben…';
}

// ── Upload senden ──────────────────────────────────────────────
async function sendUpload() {
    if (!pendingUpload) return;
    const { type, file } = pendingUpload;
    const caption = messageInput.value.trim();

    const label = type === 'audio'
        ? `🎙 Sprachnachricht (${(file.size / 1024).toFixed(1)} KB)`
        : `📎 ${file.name}`;
    addMessage(label + (caption ? `\n${caption}` : ''), 'user');
    messageCount++;

    cancelUpload();
    messageInput.value = '';
    messageInput.style.height = 'auto';
    setInputDisabled(true);
    typingIndicator.style.display = 'flex';
    scrollToBottom();

    try {
        const formData = new FormData();
        formData.append('file', file);
        if (caption) formData.append('caption', caption);

        const endpoint = type === 'audio' ? '/api/upload/audio' : '/api/upload/file';
        const res = await fetch(endpoint, { method: 'POST', body: formData });

        typingIndicator.style.display = 'none';

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'Upload fehlgeschlagen');
        }

        const data = await res.json();

        if (data.transcript) {
            addSystemMessage(`🎙 Erkannt: „${data.transcript}"`);
        }

        addMessage(data.response, 'bot', {
            intent: data.intent,
            skill: data.skill,
            thought: data.thought,
            fileTag: type === 'audio' ? '🎙 AUDIO' : `📎 ${file.name.split('.').pop().toUpperCase()}`
        });
        messageCount++;
        updateStats();

    } catch (e) {
        typingIndicator.style.display = 'none';
        addErrorMessage(e.message);
    } finally {
        setInputDisabled(false);
    }
}

// ── Text senden ────────────────────────────────────────────────
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    messageCount++;
    messageInput.value = '';
    messageInput.style.height = 'auto';
    setInputDisabled(true);
    typingIndicator.style.display = 'flex';
    scrollToBottom();

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, provider: providerSelect.value })
        });

        typingIndicator.style.display = 'none';

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.error || 'API Fehler');
        }

        const data = await res.json();
        addMessage(data.response, 'bot', {
            intent: data.intent,
            skill: data.skill,
            thought: data.thought
        });
        messageCount++;
        updateStats();

    } catch (e) {
        typingIndicator.style.display = 'none';
        addErrorMessage(e.message);
    } finally {
        setInputDisabled(false);
    }
}

// ── Nachricht rendern ──────────────────────────────────────────
function addMessage(text, type, meta = {}) {
    const wrap = document.createElement('div');
    wrap.className = `message ${type}-message`;

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = type === 'user' ? 'DU' : 'ILIJA';
    wrap.appendChild(header);

    const content = document.createElement('div');
    content.className = 'message-content';

    if (meta.fileTag) {
        const tag = document.createElement('div');
        tag.className = 'msg-file-tag';
        tag.textContent = meta.fileTag;
        content.appendChild(tag);
    }

    const textNode = document.createElement('span');
    textNode.textContent = text;
    content.appendChild(textNode);
    wrap.appendChild(content);

    if (meta.intent || meta.skill || meta.thought) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';
        if (meta.intent) {
            const b = document.createElement('span');
            b.className = 'intent-badge';
            b.textContent = meta.intent;
            metaDiv.appendChild(b);
        }
        if (meta.skill) {
            const b = document.createElement('span');
            b.className = 'skill-badge';
            b.textContent = `⬡ ${meta.skill}`;
            metaDiv.appendChild(b);
        }
        if (meta.thought) {
            const t = document.createElement('span');
            t.className = 'thought-text';
            t.textContent = `↯ ${meta.thought}`;
            metaDiv.appendChild(t);
        }
        wrap.appendChild(metaDiv);
    }

    chatContainer.appendChild(wrap);
    scrollToBottom();
}

function addSystemMessage(text) {
    const d = document.createElement('div');
    d.className = 'system-message';
    d.textContent = `— ${text} —`;
    chatContainer.appendChild(d);
    scrollToBottom();
}

function addErrorMessage(text) {
    const d = document.createElement('div');
    d.className = 'error-message';
    d.textContent = `ERR: ${text}`;
    chatContainer.appendChild(d);
    scrollToBottom();
}

// ── Chat löschen ───────────────────────────────────────────────
async function clearChat() {
    if (!confirm('Chat-Verlauf löschen?')) return;
    try {
        await fetch('/api/clear', { method: 'POST' });
        chatContainer.innerHTML = '';
        messageCount = 0;
        addMessage('Chat gelöscht. Wie kann ich helfen?', 'bot', { intent: 'SYSTEM' });
        updateStats();
    } catch (e) { addErrorMessage('Fehler beim Löschen'); }
}

// ── Helpers ────────────────────────────────────────────────────
function setInputDisabled(disabled) {
    messageInput.disabled = disabled;
    sendBtn.disabled = disabled;
    if (!disabled) messageInput.focus();
}

function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
