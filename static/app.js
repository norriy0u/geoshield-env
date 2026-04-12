/* ═══════════════════════════════════════════════════════════════════════════
   GeoShield Command Center — Frontend Logic v5.0
   Premium Tactical Dashboard with Sound, Gauge Animation, Terminal Log
   ═══════════════════════════════════════════════════════════════════════════ */

// ═══ STATE ═══════════════════════════════════════════════════════════════════
let sessionId = null;
let taskConfig = null;
let observation = null;
let totalScore = 0.0;
let soundEnabled = true;

// ═══ DOM CACHE ═══════════════════════════════════════════════════════════════
const $ = id => document.getElementById(id);

const DOM = {
    tasksList:      $('tasks-list'),
    sessionBadge:   $('session-badge'),
    missionMeta:    $('mission-meta'),
    missionStatus:  $('mission-status'),
    stepsBadge:     $('steps-badge'),
    obsDisplay:     $('observation-display'),
    actionSelect:   $('action-select'),
    executeBtn:     $('execute-btn'),
    scoreVal:       $('score-val'),
    gaugeFill:      $('gauge-fill'),
    terminalLog:    $('terminal-log'),
    actionForm:     $('action-form'),
    dynamicFields:  $('dynamic-fields'),
    feedbackBox:    $('feedback-container'),
    modal:          $('briefing-modal'),
    modalTitle:     $('modal-title'),
    modalDesc:      $('modal-desc'),
    modalScore:     $('modal-score'),
    modalIcon:      $('modal-icon'),
    modalClose:     $('modal-close'),
    clock:          $('clock'),
    soundToggle:    $('sound-toggle'),
};

// ═══ AUDIO SYSTEM (Web Audio API) ════════════════════════════════════════════
const AudioCtx = window.AudioContext || window.webkitAudioContext;
let audioCtx = null;

function initAudio() {
    if (!audioCtx) {
        try { audioCtx = new AudioCtx(); } catch(e) { /* silent fail */ }
    }
}

function playTone(freq, duration, type = 'sine', volume = 0.12) {
    if (!soundEnabled || !audioCtx) return;
    try {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gain.gain.setValueAtTime(volume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    } catch(e) { /* silent */ }
}

function sfxClick()   { playTone(800, 0.06, 'square', 0.06); }
function sfxSubmit()  { playTone(600, 0.08, 'sine', 0.08); playTone(900, 0.12, 'sine', 0.06); }
function sfxSuccess() { setTimeout(() => playTone(523, 0.15, 'sine', 0.1), 0); setTimeout(() => playTone(659, 0.15, 'sine', 0.1), 100); setTimeout(() => playTone(784, 0.25, 'sine', 0.1), 200); }
function sfxFail()    { setTimeout(() => playTone(440, 0.15, 'sawtooth', 0.08), 0); setTimeout(() => playTone(330, 0.25, 'sawtooth', 0.08), 120); }
function sfxAlert()   { playTone(880, 0.08, 'square', 0.05); setTimeout(() => playTone(880, 0.08, 'square', 0.05), 150); }

// ═══ TERMINAL LOGGER ═════════════════════════════════════════════════════════
function log(msg, type = '') {
    const time = new Date().toISOString().split('T')[1].substring(0, 8);
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `<span class="log-time">${time}</span><span class="log-msg ${type}">${msg}</span>`;
    DOM.terminalLog.appendChild(entry);
    DOM.terminalLog.scrollTop = DOM.terminalLog.scrollHeight;
}

// ═══ CLOCK ═══════════════════════════════════════════════════════════════════
function updateClock() {
    DOM.clock.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ═══ SCORE GAUGE ═════════════════════════════════════════════════════════════
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 70; // r=70

function setGauge(score) {
    const offset = GAUGE_CIRCUMFERENCE * (1 - score);
    DOM.gaugeFill.style.strokeDasharray = GAUGE_CIRCUMFERENCE;
    DOM.gaugeFill.style.strokeDashoffset = offset;

    // Color class
    DOM.gaugeFill.classList.remove('low', 'mid', 'high');
    if (score < 0.3)       DOM.gaugeFill.classList.add('low');
    else if (score < 0.65) DOM.gaugeFill.classList.add('mid');
    else                   DOM.gaugeFill.classList.add('high');
}

function animateScore(start, end) {
    const duration = 800;
    const startTime = performance.now();

    function tick(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;

        DOM.scoreVal.textContent = current.toFixed(2);
        setGauge(current);

        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ═══ MISSION STATUS ══════════════════════════════════════════════════════════
function setMissionStatus(status) {
    DOM.missionStatus.className = 'mission-status ' + status;
    const labels = { idle: 'STANDBY', active: 'ACTIVE', complete: 'COMPLETE', failed: 'FAILED' };
    DOM.missionStatus.textContent = labels[status] || status.toUpperCase();
}

// ═══ LOAD TASKS ══════════════════════════════════════════════════════════════
async function loadTasks() {
    log('Connecting to GeoShield Command Node...', 'info');
    try {
        const res = await fetch('/tasks');
        const data = await res.json();
        DOM.tasksList.innerHTML = '';

        data.tasks.forEach(task => {
            const card = document.createElement('div');
            card.className = 'task-card';
            const diffClass = 'diff-' + task.difficulty;
            card.innerHTML = `
                <div class="task-id">OP-${task.task_id}00</div>
                <div class="task-name">${task.name}</div>
                <div class="task-diff">
                    <span class="diff-badge ${diffClass}">${task.difficulty}</span>
                    ${task.actions.length} actions
                </div>
            `;
            card.onclick = () => { initAudio(); sfxClick(); startMission(task, card); };
            DOM.tasksList.appendChild(card);
        });

        log('Mission directory loaded — 4 operations available.', 'success');
        log('Select a mission to begin intelligence analysis.', '');
    } catch (e) {
        log('ERROR: Failed to connect to Command Node.', 'error');
    }
}

// ═══ START MISSION ═══════════════════════════════════════════════════════════
async function startMission(task, cardElement) {
    // Highlight active card
    document.querySelectorAll('.task-card').forEach(c => c.classList.remove('active'));
    if (cardElement) cardElement.classList.add('active');

    taskConfig = task;
    log(`Initializing OP-${task.task_id}00: ${task.name}...`, 'info');
    setMissionStatus('active');

    try {
        const res = await fetch('/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: task.task_id })
        });
        const data = await res.json();

        sessionId = data.session_id;
        totalScore = 0.0;
        DOM.scoreVal.textContent = '0.00';
        setGauge(0);
        DOM.sessionBadge.textContent = sessionId.split('-')[0].toUpperCase();
        DOM.feedbackBox.innerHTML = '';

        processObservation(data.observation);
        sfxAlert();
        log(`Uplink established. Case: ${data.observation.case_id}`, 'success');
        log(`Difficulty: ${data.observation.difficulty.toUpperCase()} | Task: ${task.name}`, '');
    } catch (e) {
        log(`ERROR: Reset failed — ${e.message}`, 'error');
        setMissionStatus('failed');
    }
}

// ═══ PROCESS OBSERVATION ═════════════════════════════════════════════════════
function processObservation(obs) {
    observation = obs;

    // Mission meta
    DOM.missionMeta.textContent = `CASE ${obs.case_id} · STEP ${obs.step} · ${obs.difficulty.toUpperCase()}`;

    // Steps badge
    if (obs.steps_remaining != null) {
        DOM.stepsBadge.style.display = 'inline-block';
        DOM.stepsBadge.textContent = `${obs.steps_remaining} STEPS LEFT`;
    } else {
        DOM.stepsBadge.style.display = 'none';
    }

    // Build observation HTML
    let html = '';

    if (obs.report) {
        html += `
            <div class="data-card">
                <div class="data-label">⬡ Intelligence Report</div>
                <div class="data-content">${obs.report}</div>
            </div>`;
    }

    if (obs.context) {
        html += `
            <div class="data-card">
                <div class="data-label">◇ Situational Context</div>
                <div class="data-content">${obs.context}</div>
            </div>`;
    }

    if (obs.sectors && obs.sectors.length) {
        html += `<div class="data-label" style="margin-bottom:12px;">◈ Sector Intelligence</div>`;
        html += '<div class="sector-grid">';
        obs.sectors.forEach(s => {
            const conf = (s.confidence * 100).toFixed(0);
            const confClass = s.confidence >= 0.7 ? 'high' : s.confidence >= 0.4 ? 'med' : 'low';
            html += `
                <div class="sector-card">
                    <div class="sector-id">${s.sector_id.replace('_', ' ')}</div>
                    <div class="sector-summary">${s.summary}</div>
                    <div class="sector-anomaly">TYPE: ${(s.anomaly_type || 'unknown').replace('_', ' ')}</div>
                    <div class="confidence-bar"><div class="confidence-fill ${confClass}" style="width:${conf}%"></div></div>
                    <div class="confidence-label">CONF ${conf}%</div>
                </div>`;
        });
        html += '</div>';
    }

    if (obs.investigation_results && Object.keys(obs.investigation_results).length) {
        html += `
            <div class="data-card">
                <div class="data-label">⊕ Investigation Data</div>
                <div class="data-content"><pre>${JSON.stringify(obs.investigation_results, null, 2)}</pre></div>
            </div>`;
    }

    if (obs.hint) {
        html += `
            <div class="data-card" style="border-color: var(--border-glow);">
                <div class="data-label" style="color: var(--warning);">△ Operational Hint</div>
                <div class="data-content" style="color: var(--text-secondary);">${obs.hint}</div>
            </div>`;
    }

    if (obs.available_assets) {
        html += `
            <div class="data-card">
                <div class="data-label">⬢ Available Assets</div>
                <div class="data-content">${obs.available_assets}</div>
            </div>`;
    }

    DOM.obsDisplay.innerHTML = html;

    // Populate actions dropdown
    DOM.actionSelect.innerHTML = '<option value="">Select action...</option>';
    obs.available_actions.forEach(act => {
        const opt = document.createElement('option');
        opt.value = act;
        opt.textContent = act.toUpperCase().replaceAll('_', ' ');
        DOM.actionSelect.appendChild(opt);
    });

    DOM.actionSelect.disabled = false;
    DOM.executeBtn.disabled = false;
    buildDynamicFields(obs.task_id);
}

// ═══ DYNAMIC FORM FIELDS ═════════════════════════════════════════════════════
function buildDynamicFields(taskId) {
    let html = '';

    if (taskId === 2) {
        html += `
            <div class="form-group">
                <label for="field-severity">Threat Severity (1–10)</label>
                <input type="number" id="field-severity" min="1" max="10" value="5" required class="form-control">
            </div>`;
    }

    if (taskId === 3 || taskId === 4) {
        html += `
            <div class="form-group">
                <label for="field-reasoning">Strategic Reasoning</label>
                <textarea id="field-reasoning" placeholder="Document your analysis logic..." required class="form-control"></textarea>
            </div>`;
    }

    if (taskId === 4) {
        html += `
            <div class="form-group">
                <label for="field-deception">Deception Type</label>
                <select id="field-deception" class="form-control">
                    <option value="">Select classification...</option>
                    <option value="civilian_military">Civilian / Military Dual-Use</option>
                    <option value="commercial_weapons">Commercial Weapons Cover</option>
                    <option value="construction_fortification">Construction Fortification</option>
                    <option value="logistics_supply">Logistics Supply Hub</option>
                    <option value="research_weapons">Research Weapons Front</option>
                </select>
            </div>
            <div class="form-group">
                <label for="field-cover">Cover Story Identified</label>
                <input type="text" id="field-cover" placeholder="e.g. agricultural research" class="form-control">
            </div>`;
    }

    DOM.dynamicFields.innerHTML = html;
}

// ═══ SUBMIT ACTION ═══════════════════════════════════════════════════════════
DOM.actionForm.onsubmit = async (e) => {
    e.preventDefault();
    if (!sessionId) return;

    DOM.executeBtn.disabled = true;
    DOM.executeBtn.textContent = '⏳ PROCESSING...';
    const action = DOM.actionSelect.value;
    if (!action) { DOM.executeBtn.disabled = false; DOM.executeBtn.textContent = '▶ EXECUTE DECISION'; return; }

    sfxSubmit();
    log(`Executing: ${action.toUpperCase().replaceAll('_', ' ')}`, 'info');

    const payload = { action, session_id: sessionId };

    // Gather dynamic fields
    const eSev = document.getElementById('field-severity');
    if (eSev && action !== 'ignore') payload.threat_level = parseInt(eSev.value);

    if (action.startsWith('deploy_') || action.startsWith('investigate_')) {
        payload.target_sector = action.replace('deploy_to_', '').replace('investigate_', '');
    }

    const eRea = document.getElementById('field-reasoning');
    if (eRea) payload.reasoning = eRea.value;

    const eDec = document.getElementById('field-deception');
    if (eDec && action === 'covert_operation') payload.deception_type = eDec.value;

    const eCov = document.getElementById('field-cover');
    if (eCov && action === 'covert_operation') payload.cover_story_identified = eCov.value;

    try {
        const res = await fetch('/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        const stepReward = data.reward || 0;
        const newTotal = data.info?.total_score || stepReward;
        const oldTotal = totalScore;
        totalScore = newTotal;

        log(`Reward: +${stepReward.toFixed(2)} → Total: ${newTotal.toFixed(2)}`, stepReward >= 0.5 ? 'success' : 'warn');
        animateScore(oldTotal, newTotal);

        // Show feedback
        if (data.info) renderFeedback(data.info);

        if (data.done) {
            handleEpisodeEnd(data);
        } else {
            processObservation(data.observation);
            DOM.executeBtn.disabled = false;
        }
    } catch (err) {
        log(`ERROR: ${err.message}`, 'error');
        sfxFail();
        DOM.executeBtn.disabled = false;
    }

    DOM.executeBtn.textContent = '▶ EXECUTE DECISION';
};

// ═══ FEEDBACK PANEL ══════════════════════════════════════════════════════════
function renderFeedback(info) {
    let html = `<div class="feedback-card">
        <div class="feedback-title">⊞ Grading Feedback</div>`;

    if (info.feedback) {
        html += `<div class="feedback-text">${info.feedback}</div>`;
    }

    if (info.breakdown && Object.keys(info.breakdown).length) {
        html += '<div class="breakdown-grid">';
        for (const [key, val] of Object.entries(info.breakdown)) {
            const displayVal = typeof val === 'number' ? val.toFixed(2) : val;
            const displayKey = key.replaceAll('_', ' ');
            html += `<div class="breakdown-item"><span class="label">${displayKey}</span><span class="value">${displayVal}</span></div>`;
        }
        html += '</div>';
    }

    html += '</div>';
    DOM.feedbackBox.innerHTML = html;
}

// ═══ EPISODE END ═════════════════════════════════════════════════════════════
function handleEpisodeEnd(data) {
    DOM.actionSelect.disabled = true;
    DOM.executeBtn.disabled = true;
    DOM.executeBtn.textContent = 'MISSION CONCLUDED';

    const isSuccess = totalScore >= 0.5;

    // Status
    setMissionStatus(isSuccess ? 'complete' : 'failed');
    log(`═════ MISSION ${isSuccess ? 'SUCCESS' : 'COMPLETE'} ═════`, isSuccess ? 'success' : 'warn');
    log(`Final Score: ${totalScore.toFixed(2)}`, isSuccess ? 'success' : 'warn');

    // Sound
    if (isSuccess) sfxSuccess(); else sfxFail();

    // Modal
    DOM.modalIcon.className = 'modal-icon ' + (isSuccess ? 'success' : 'failure');
    DOM.modalIcon.textContent = isSuccess ? '✓' : '✗';
    DOM.modalTitle.textContent = isSuccess ? 'Mission Success' : 'Mission Complete';
    DOM.modalTitle.style.color = isSuccess ? 'var(--success)' : 'var(--danger)';
    DOM.modalScore.textContent = totalScore.toFixed(2);
    DOM.modalScore.style.color = isSuccess ? 'var(--success)' : 'var(--danger)';
    DOM.modalDesc.textContent = isSuccess ? 'Excellent analysis, Commander.' : 'Review your assessment approach.';
    DOM.modal.classList.remove('hidden');
}

// ═══ MODAL ═══════════════════════════════════════════════════════════════════
DOM.modalClose.onclick = () => {
    DOM.modal.classList.add('hidden');
    sfxClick();
};

// Close modal on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !DOM.modal.classList.contains('hidden')) {
        DOM.modal.classList.add('hidden');
        sfxClick();
    }
});

// ═══ SOUND TOGGLE ════════════════════════════════════════════════════════════
DOM.soundToggle.onclick = () => {
    initAudio();
    soundEnabled = !soundEnabled;
    DOM.soundToggle.textContent = soundEnabled ? '🔊' : '🔇';
    DOM.soundToggle.classList.toggle('active', soundEnabled);
};

// ═══ KEYBOARD SHORTCUT (Ctrl+Enter to submit) ═══════════════════════════════
document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (!DOM.executeBtn.disabled) {
            DOM.actionForm.requestSubmit();
        }
    }
});

// ═══ INIT ════════════════════════════════════════════════════════════════════
window.onload = () => {
    loadTasks();
    setGauge(0);
    log('GeoShield Command Center initialized.', 'info');
    log('Awaiting mission selection...', '');
};
