/**
 * Wenup Intake Assistant - Client Application
 */

const STATE = {
    sessionId: null,
    turnCount: 0,
    state: null,
    pendingClarification: null,
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
const elAuditCount = document.getElementById('audit-count');
const elRawStateJson = document.getElementById('raw-state-json');
const elDocContent = document.getElementById('doc-content');
const elDocCompletionBadge = document.getElementById('doc-completion-badge');
const elBtnCopyDoc = document.getElementById('btn-copy-doc');
const elBtnDownloadPdf = document.getElementById('btn-download-pdf');
const elBtnManualEditToggle = document.getElementById('btn-manual-edit-toggle');
const elManualEditPanel = document.getElementById('manual-edit-panel');
const elManualEditForm = document.getElementById('manual-edit-form');
const elBtnCancelEdit = document.getElementById('btn-cancel-edit');
const elEditFieldSelect = document.getElementById('edit-field-select');
const elEditFieldValue = document.getElementById('edit-field-value');
const elQuickRepliesBar = document.getElementById('quick-replies-bar');

// SVG Icons for fields matching the design
const ICONS = {
    user: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,
    home: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`,
    globe: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>`,
    users: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
    child: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="5"></circle><path d="M20 21a8 8 0 1 0-16 0"></path></svg>`,
    executor: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><polyline points="17 11 19 13 23 9"></polyline></svg>`,
    link: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>`,
    gift: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 12 20 22 4 22 4 12"></polyline><rect x="2" y="7" width="20" height="5"></rect><line x1="12" y1="22" x2="12" y2="7"></line><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"></path><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"></path></svg>`,
    doc: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`
};

const FIELD_SPECS = [
    { key: 'full_name', label: 'Full Legal Name', icon: ICONS.user },
    { key: 'home_address', label: 'Home Address', icon: ICONS.home },
    { key: 'covers_worldwide_assets', label: 'Covers Worldwide Assets', icon: ICONS.globe },
    { key: 'has_children', label: 'Has Children', icon: ICONS.users },
    { key: 'children', label: 'Children', icon: ICONS.child },
    { key: 'executor.name', label: 'Executor Name', icon: ICONS.executor },
    { key: 'executor.relationship', label: 'Executor Relationship', icon: ICONS.link },
    { key: 'specific_gifts', label: 'Specific Gifts & Bequests', icon: ICONS.gift },
    { key: 'additional_wishes', label: 'Additional Wishes', icon: ICONS.doc }
];

// Initialize Session
async function initSession() {
    try {
        const res = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        if (!res.ok) throw new Error('Failed to create session');
        const data = await res.json();
        STATE.sessionId = data.session_id;
        elSessionId.textContent = STATE.sessionId.slice(0, 8) + '...';
        elSessionId.title = STATE.sessionId;

        elChatMessages.innerHTML = '';
        appendMessage('assistant', 'Hello! I am your personal intake assistant for recording your personal wishes. To get started, what is your full legal name?');
        
        await syncSession();
        renderQuickReplies(["Amar Akbar Anthony", "Somesh Sinha", "John Doe"]);
    } catch (err) {
        console.error('Session initialization error:', err);
        elSessionId.textContent = 'Error';
    }
}

// Fetch current session details
async function syncSession() {
    if (!STATE.sessionId) return;
    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        
        STATE.state = data.state;
        STATE.pendingClarification = data.pending_clarification;
        STATE.turnCount = (data.messages || []).length;
        
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
    elQuickRepliesBar.innerHTML = '';

    try {
        const res = await fetch(`/api/sessions/${STATE.sessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: content })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Message sending failed');
        }

        const data = await res.json();
        appendMessage('assistant', data.assistant_message);
        
        STATE.state = data.state;
        STATE.pendingClarification = data.pending_clarification;
        STATE.turnCount = (STATE.turnCount || 0) + 1;
        
        updateStateUI();
        await updateDocumentPreview();
        updateQuickReplies(data.assistant_message);
    } catch (err) {
        console.error('Send error:', err);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        elBtnSend.disabled = false;
        elChatInput.focus();
    }
}

// Append Chat Message Row
function appendMessage(role, text) {
    const row = document.createElement('div');
    row.className = `chat-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar-icon-box ${role}`;
    avatar.innerHTML = role === 'user' 
        ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`
        : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><polygon points="12 6 12 12 16 14"/></svg>`;

    const wrap = document.createElement('div');
    wrap.className = 'chat-bubble-wrap';

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = text;

    const time = document.createElement('div');
    time.className = 'chat-bubble-time';
    const now = new Date();
    time.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    wrap.appendChild(bubble);
    wrap.appendChild(time);

    row.appendChild(avatar);
    row.appendChild(wrap);

    elChatMessages.appendChild(row);
    elChatMessages.scrollTop = elChatMessages.scrollHeight;
}

// Quick reply buttons
function updateQuickReplies(msg) {
    const lower = (msg || '').toLowerCase();
    if (lower.includes('children') || lower.includes('any children')) {
        renderQuickReplies(["No, I don't have any children", "Yes, I have children", "Prefer not to say"]);
    } else if (lower.includes('outside') || lower.includes('worldwide') || lower.includes('assets')) {
        renderQuickReplies(["Yes, I have assets worldwide", "No, domestic only", "Yes"]);
    } else if (lower.includes('executor') || lower.includes('appoint')) {
        renderQuickReplies(["My spouse", "My eldest child", "A trusted friend"]);
    } else if (lower.includes('address')) {
        renderQuickReplies(["123 Main Street, Apt 4B, New York, NY 10001", "I2IT College, Hinjewadi, Pune"]);
    } else {
        elQuickRepliesBar.innerHTML = '';
    }
}

function renderQuickReplies(chips) {
    elQuickRepliesBar.innerHTML = '';
    if (!chips || chips.length === 0) return;

    chips.forEach(text => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'quick-reply-btn';
        btn.textContent = text;
        btn.addEventListener('click', () => {
            elChatInput.value = text;
            sendMessage(text);
        });
        elQuickRepliesBar.appendChild(btn);
    });
}

// Update State Column UI
function updateStateUI() {
    elTurnCounter.textContent = `Turn ${STATE.turnCount}`;

    if (!STATE.state) return;

    // Check contradiction banner
    if (STATE.pendingClarification && STATE.pendingClarification.issue_type === 'contradiction') {
        elContradictionBanner.classList.remove('hidden');
        elContradictionMsg.textContent = STATE.pendingClarification.prompt || 'A conflict was found with previously confirmed information.';
    } else {
        elContradictionBanner.classList.add('hidden');
    }

    // Render Fields
    elFieldsGrid.innerHTML = '';
    const fieldMap = {
        'full_name': STATE.state.full_name,
        'home_address': STATE.state.home_address,
        'covers_worldwide_assets': STATE.state.covers_worldwide_assets,
        'has_children': STATE.state.has_children,
        'children': STATE.state.children,
        'executor.name': STATE.state.executor?.name,
        'executor.relationship': STATE.state.executor?.relationship,
        'specific_gifts': STATE.state.specific_gifts,
        'additional_wishes': STATE.state.additional_wishes
    };

    FIELD_SPECS.forEach(({ key, label, icon }) => {
        const field = fieldMap[key];
        if (!field) return;

        const row = document.createElement('div');
        row.className = 'field-row-item';
        row.title = `Click to edit ${label}`;

        row.addEventListener('click', () => {
            elManualEditPanel.classList.remove('hidden');
            elEditFieldSelect.value = key;
            elEditFieldValue.value = typeof field.value === 'object' ? JSON.stringify(field.value) : (field.value ?? '');
            elEditFieldValue.focus();
        });

        const left = document.createElement('div');
        left.className = 'field-left';

        const iconBox = document.createElement('div');
        iconBox.className = 'field-icon-box';
        iconBox.innerHTML = icon;

        const texts = document.createElement('div');
        texts.className = 'field-texts';

        const nameSpan = document.createElement('span');
        nameSpan.className = 'field-label';
        nameSpan.textContent = label;

        const valSpan = document.createElement('span');
        valSpan.className = 'field-val-text' + (field.value === null || field.value === undefined ? ' empty' : '');

        let displayVal = field.value;
        if (displayVal === null || displayVal === undefined) {
            displayVal = '—';
        } else if (Array.isArray(displayVal)) {
            displayVal = displayVal.length > 0 ? displayVal.join(', ') : 'None';
        } else if (typeof displayVal === 'boolean') {
            displayVal = displayVal ? 'Yes' : 'No';
        }

        valSpan.textContent = displayVal;

        texts.appendChild(nameSpan);
        texts.appendChild(valSpan);
        left.appendChild(iconBox);
        left.appendChild(texts);

        const right = document.createElement('div');
        right.className = 'field-right';

        const statusRaw = (field.status || 'unknown').toLowerCase().replace('_', '-');
        const badge = document.createElement('span');
        badge.className = `status-badge ${statusRaw}`;
        badge.textContent = (field.status || 'UNKNOWN').replace('_', ' ');

        const chevron = document.createElement('span');
        chevron.className = 'chevron-arrow';
        chevron.textContent = '›';

        right.appendChild(badge);
        right.appendChild(chevron);

        row.appendChild(left);
        row.appendChild(right);
        elFieldsGrid.appendChild(row);
    });

    // Render Changes
    const changes = STATE.state.change_history || [];
    elChangeHistory.innerHTML = '';
    if (elAuditCount) elAuditCount.textContent = changes.length;

    if (changes.length === 0) {
        elChangeHistory.innerHTML = '<span class="empty-text">No changes recorded yet.</span>';
    } else {
        changes.slice(-10).reverse().forEach(ch => {
            const item = document.createElement('div');
            item.className = 'change-history-item';
            item.innerHTML = `<strong>${ch.field}</strong>: <span>${JSON.stringify(ch.old_val)} → ${JSON.stringify(ch.new_val)}</span> (${ch.kind})`;
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
        elDocContent.textContent = data.text || 'No document content generated yet.';
        
        if (data.is_complete) {
            elDocCompletionBadge.textContent = '100% Complete';
            elDocCompletionBadge.className = 'badge-status-pill complete';
        } else {
            const missingCount = (data.missing_fields || []).length;
            const completedCount = 7 - missingCount;
            const pct = Math.max(0, Math.min(100, Math.round((completedCount / 7) * 100)));
            elDocCompletionBadge.textContent = `${pct}% Complete (${missingCount} missing)`;
            elDocCompletionBadge.className = 'badge-status-pill';
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
    if (confirm('Start a new intake session? Current progress will be reset.')) {
        initSession();
    }
});

elBtnCopyDoc.addEventListener('click', () => {
    if (STATE.document && STATE.document.text) {
        navigator.clipboard.writeText(STATE.document.text).then(() => {
            const originalHTML = elBtnCopyDoc.innerHTML;
            elBtnCopyDoc.textContent = 'Copied!';
            setTimeout(() => { elBtnCopyDoc.innerHTML = originalHTML; }, 2000);
        });
    }
});

if (elBtnDownloadPdf) {
    elBtnDownloadPdf.addEventListener('click', () => {
        window.print();
    });
}

elBtnManualEditToggle.addEventListener('click', () => {
    elManualEditPanel.classList.toggle('hidden');
    if (!elManualEditPanel.classList.contains('hidden')) {
        elEditFieldValue.focus();
    }
});

elBtnCancelEdit.addEventListener('click', () => {
    elManualEditPanel.classList.add('hidden');
});

elManualEditForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const field = elEditFieldSelect.value;
    const rawVal = elEditFieldValue.value;

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
                field: field,
                op: 'set',
                value: parsedVal
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

// Document navigation links click handler
document.querySelectorAll('.doc-nav-link').forEach(link => {
    link.addEventListener('click', () => {
        document.querySelectorAll('.doc-nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
    });
});

// Boot
initSession();
