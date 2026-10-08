/**
 * Wenup Intake Assistant - Client Application
 */

const STATE = {
    sessionId: null,
    turnCount: 0,
    state: null,
    pendingClarifications: [],
    document: null
};

// DOM Elements
const elSessionId = document.getElementById('session-id-display');
const elTurnCounter = document.getElementById('turn-counter');
const elChatMessages = document.getElementById('chat-messages');
const elChatForm = document.getElementById('chat-form');
const elChatInput = document.getElementById('chat-input');
const elBtnSend = document.getElementById('btn-send');
const elBtnNewSession = document.getElementById('btn-new-session');
const elContradictionBanner = document.getElementById('contradiction-banner');
const elContradictionMsg = document.getElementById('contradiction-message');
const elFieldsGrid = document.getElementById('fields-grid');
const elChangeHistory = document.getElementById('change-history');
const elRawStateJson = document.getElementById('raw-state-json');
const elDocContent = document.getElementById('doc-content');
const elDocCompletionBadge = document.getElementById('doc-completion-badge');
const elBtnCopyDoc = document.getElementById('btn-copy-doc');
const elBtnManualEditToggle = document.getElementById('btn-manual-edit-toggle');
const elManualEditPanel = document.getElementById('manual-edit-panel');
const elManualEditForm = document.getElementById('manual-edit-form');
const elBtnCancelEdit = document.getElementById('btn-cancel-edit');

// Initialize Session
async function initSession() {
    try {
        const res = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ client_id: 'browser_user' })
        });
        if (!res.ok) throw new Error('Failed to create session');
        const data = await res.json();
        STATE.sessionId = data.session_id;
        elSessionId.textContent = STATE.sessionId.slice(0, 8) + '...';
        elSessionId.title = STATE.sessionId;

        // Clear UI
        elChatMessages.innerHTML = '';
        appendMessage('assistant', 'Hello! I am your personal intake assistant for recording your personal wishes. To get started, what is your full legal name?');
        
        await syncSession();
    } catch (err) {
        console.error('Session initialization error:', err);
        elSessionId.textContent = 'Error creating session';
    }
}

// Fetch full session details
async function syncSession() {
    if (!STATE.sessionId) return;
    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        
        STATE.state = data.state;
        STATE.pendingClarifications = data.pending_clarifications || [];
        STATE.turnCount = data.turn_count || 0;
        
        updateStateUI();
        await updateDocumentPreview();
    } catch (err) {
        console.error('Failed to sync session:', err);
    }
}

// Send Message
async function sendMessage(content) {
    if (!content.trim() || !STATE.sessionId) return;

    appendMessage('user', content);
    elChatInput.value = '';
    elBtnSend.disabled = true;

    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Message sending failed');
        }

        const data = await res.json();
        appendMessage('assistant', data.assistant_message);
        
        STATE.state = data.state;
        STATE.pendingClarifications = data.pending_clarifications || [];
        STATE.turnCount = (STATE.turnCount || 0) + 1;
        
        updateStateUI();
        await updateDocumentPreview();
    } catch (err) {
        console.error('Send error:', err);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        elBtnSend.disabled = false;
        elChatInput.focus();
    }
}

// Append chat message
function appendMessage(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    
    const content = document.createElement('div');
    content.className = 'chat-bubble-content';
    content.textContent = text;
    bubble.appendChild(content);

    const meta = document.createElement('div');
    meta.className = 'chat-bubble-meta';
    meta.textContent = role === 'user' ? 'You' : 'Assistant';
    bubble.appendChild(meta);

    elChatMessages.appendChild(bubble);
    elChatMessages.scrollTop = elChatMessages.scrollHeight;
}

// Update State Column UI
function updateStateUI() {
    elTurnCounter.textContent = `Turn ${STATE.turnCount}`;

    if (!STATE.state) return;

    // Check contradiction banner
    const contradictions = STATE.pendingClarifications.filter(c => c.issue_type === 'contradiction');
    if (contradictions.length > 0) {
        elContradictionBanner.classList.remove('hidden');
        elContradictionMsg.textContent = contradictions.map(c => c.prompt).join(' | ');
    } else {
        elContradictionBanner.classList.add('hidden');
    }

    // Render Fields
    elFieldsGrid.innerHTML = '';
    const fieldOrder = [
        'full_name', 'jurisdiction', 'marital_status', 
        'covers_worldwide_assets', 'has_children', 'children',
        'primary_beneficiaries', 'executor_name', 'has_digital_assets', 'additional_wishes'
    ];

    fieldOrder.forEach(fieldName => {
        const field = STATE.state[fieldName];
        if (!field) return;

        const card = document.createElement('div');
        card.className = 'field-card';

        const top = document.createElement('div');
        top.className = 'field-card-top';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'field-name';
        nameSpan.textContent = fieldName;

        const badge = document.createElement('span');
        badge.className = `badge badge-${field.status.toLowerCase().replace('_', '-')}`;
        badge.textContent = field.status;

        top.appendChild(nameSpan);
        top.appendChild(badge);

        const valSpan = document.createElement('div');
        valSpan.className = 'field-value' + (field.value === null ? ' empty' : '');
        
        let displayVal = field.value;
        if (displayVal === null) {
            displayVal = '—';
        } else if (Array.isArray(displayVal)) {
            displayVal = displayVal.length > 0 ? displayVal.join(', ') : '[] (None)';
        } else if (typeof displayVal === 'boolean') {
            displayVal = displayVal ? 'Yes (true)' : 'No (false)';
        }

        valSpan.textContent = displayVal;

        card.appendChild(top);
        card.appendChild(valSpan);
        elFieldsGrid.appendChild(card);
    });

    // Render Audit History
    const history = STATE.state.change_history || [];
    elChangeHistory.innerHTML = '';
    if (history.length === 0) {
        elChangeHistory.innerHTML = '<span class="empty-state">No changes recorded yet.</span>';
    } else {
        history.slice(-10).reverse().forEach(ch => {
            const item = document.createElement('div');
            item.className = 'change-item';
            item.innerHTML = `<strong>${ch.field}</strong>: <span>${JSON.stringify(ch.old_val)} → ${JSON.stringify(ch.new_val)}</span> <span class="badge badge-muted">${ch.kind}</span>`;
            elChangeHistory.appendChild(item);
        });
    }

    // Render Raw JSON
    elRawStateJson.textContent = JSON.stringify(STATE.state, null, 2);
}

// Update Document Preview
async function updateDocumentPreview() {
    if (!STATE.sessionId) return;
    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}/document`);
        if (!res.ok) return;
        const data = await res.json();
        
        STATE.document = data;
        elDocContent.textContent = data.markdown_text || 'No document content available.';
        
        const pct = Math.round(data.completion_ratio * 100);
        elDocCompletionBadge.textContent = `${pct}% Complete`;
        if (pct >= 80) {
            elDocCompletionBadge.className = 'badge badge-confirmed';
        } else if (pct >= 40) {
            elDocCompletionBadge.className = 'badge badge-unconfirmed';
        } else {
            elDocCompletionBadge.className = 'badge badge-warning';
        }
    } catch (err) {
        console.error('Document preview error:', err);
    }
}

// Event Listeners
elChatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage(elChatInput.value);
});

elChatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(elChatInput.value);
    }
});

elBtnNewSession.addEventListener('click', () => {
    if (confirm('Start a new intake session? Current progress in this tab will be reset.')) {
        initSession();
    }
});

elBtnCopyDoc.addEventListener('click', () => {
    if (STATE.document && STATE.document.markdown_text) {
        navigator.clipboard.writeText(STATE.document.markdown_text).then(() => {
            const originalText = elBtnCopyDoc.innerHTML;
            elBtnCopyDoc.textContent = 'Copied!';
            setTimeout(() => { elBtnCopyDoc.innerHTML = originalText; }, 2000);
        });
    }
});

elBtnManualEditToggle.addEventListener('click', () => {
    elManualEditPanel.classList.toggle('hidden');
});

elBtnCancelEdit.addEventListener('click', () => {
    elManualEditPanel.classList.add('hidden');
});

elManualEditForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const field = document.getElementById('edit-field-select').value;
    const rawVal = document.getElementById('edit-field-value').value;
    const status = document.getElementById('edit-field-status').value;

    let parsedVal = rawVal;
    if (rawVal.toLowerCase() === 'true') parsedVal = true;
    else if (rawVal.toLowerCase() === 'false') parsedVal = false;
    else if (rawVal.startsWith('[') && rawVal.endsWith(']')) {
        try { parsedVal = JSON.parse(rawVal); } catch (_) {}
    }

    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}/state`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                field_name: field,
                value: parsedVal,
                status: status
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Edit failed: ${err.detail || 'Unknown error'}`);
            return;
        }

        const data = await res.json();
        STATE.state = data.state;
        updateStateUI();
        await updateDocumentPreview();
        elManualEditPanel.classList.add('hidden');
    } catch (err) {
        alert(`Error applying edit: ${err.message}`);
    }
});

// Boot
initSession();
