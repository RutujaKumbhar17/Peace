// diary.js - Advanced Dynamic Journaling for Project Peace

// --- CONFIGURATION ---
const TEMPLATES = {
    "Custom Note": [
        { label: "Your Thoughts", type: "textarea", key: "content", placeholder: "Write anything..." },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. reflection, work, personal" }
    ],
    "Daily Reflection": [
        { label: "Today I Feel", type: "text", key: "mood_text", placeholder: "Summarize your mood..." },
        { label: "Today's Highlights", type: "list", key: "highlights", count: 3, placeholder: "Highlight #" },
        { label: "What I Learned", type: "textarea", key: "lessons", placeholder: "A lesson from today..." },
        { label: "Gratitude", type: "textarea", key: "gratitude", placeholder: "What are you thankful for?" },
        { label: "Improvement", type: "textarea", key: "improvement", placeholder: "What could have been better?" },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. daily, reflection" }
    ],
    "Productivity": [
        { label: "Top 3 Priorities", type: "list", key: "priorities", count: 3, placeholder: "Priority #" },
        { label: "Productivity Score", type: "range", key: "score", min: 1, max: 10 },
        { label: "To-Do List", type: "todo", key: "todos" },
        { label: "Reasoning", type: "textarea", key: "reasoning", placeholder: "Why was today productive (or not)?" },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. goals, work" }
    ],
    "Mood Tracker": [
        { label: "Select Your Vibe", type: "emoji", key: "mood_emoji" },
        { label: "Factors Affecting Mood", type: "textarea", key: "factors", placeholder: "Work, health, people..." },
        { label: "Smile Moment", type: "textarea", key: "smile", placeholder: "What made you smile today?" },
        { label: "Self-Care Habits", type: "textarea", key: "self_care", placeholder: "What did you do for yourself?" },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. mentalhealth, mood" }
    ],
    "Weekly Growth": [
        { label: "Achievement of the Week", type: "textarea", key: "achievement" },
        { label: "Biggest Challenge", type: "textarea", key: "challenge" },
        { label: "Skills Improved", type: "textarea", key: "skills" },
        { label: "Next Week Goals", type: "list", key: "next_goals", count: 3, placeholder: "Goal #" },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. weekly, growth" }
    ],
    "Future Vision": [
        { label: "Academic Goal", type: "textarea", key: "academic" },
        { label: "Career Goal", type: "textarea", key: "career" },
        { label: "Dream Life Vision", type: "textarea", key: "dream" },
        { label: "Immediate Steps", type: "list", key: "steps", count: 3, placeholder: "Step #" },
        { label: "Tags", type: "tags", key: "tags", placeholder: "e.g. future, vision" }
    ]
};

// --- STATE ---
let activeEntryId = null;
let activeTemplate = "Daily Reflection";
let entries = [];
let calendar = null;

// --- DOM ELEMENTS ---
const dynamicFields = document.getElementById('dynamic-fields');
const entriesList = document.getElementById('entries-list');
const entryTitle = document.getElementById('entry-title');
const saveBtn = document.getElementById('save-btn');
const deleteBtn = document.getElementById('delete-btn');
const syncTime = document.getElementById('sync-time');
const activeTemplateLabel = document.getElementById('active-template-label');

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    await fetchEntries();
    initCalendar();
    selectTemplate("Custom Note");
    setupReminders();
});

// --- CORE LOGIC ---

async function fetchEntries() {
    try {
        const response = await fetch('/api/diary/entries');
        const result = await response.json();
        if (result.status === 'success') {
            entries = result.entries;
            renderEntriesList();
            if (calendar) {
                calendar.removeAllEvents();
                calendar.addEventSource(mapEntriesToEvents());
            }
        }
    } catch (err) {
        console.error("Failed to fetch entries", err);
    }
}

function renderEntriesList() {
    entriesList.innerHTML = '';
    if (entries.length === 0) {
        entriesList.innerHTML = `
            <div class="flex flex-col items-center justify-center h-40 opacity-20">
                <i class="fas fa-ghost text-2xl mb-2"></i>
                <span class="text-[10px] uppercase tracking-widest">No entries yet</span>
            </div>`;
        return;
    }

    entries.forEach(entry => {
        const tags = entry.data.tags ? entry.data.tags.split(',').map(t => t.trim()).filter(t => t) : [];
        const div = document.createElement('div');
        div.className = `entry-item ${entry.id === activeEntryId ? 'active' : ''}`;
        div.innerHTML = `
            <div class="flex justify-between items-start mb-2 pr-8">
                <div class="snippet-title text-sm font-bold truncate">${entry.title || 'Untitled'}</div>
                <div class="text-[9px] opacity-30 uppercase whitespace-nowrap">${new Date(entry.date).toLocaleDateString()}</div>
            </div>
            <div class="flex flex-wrap gap-1 mb-1">
                ${tags.map(t => `<span class="tag-badge">#${t}</span>`).join('')}
            </div>
            <div class="text-[10px] text-accent opacity-60 uppercase tracking-widest font-bold">${entry.template}</div>
            <i class="fas fa-pen-nib edit-icon"></i>
        `;
        div.onclick = () => loadEntry(entry.id);
        entriesList.appendChild(div);
    });
}

function selectTemplate(name) {
    activeTemplate = name;
    activeTemplateLabel.innerText = name;
    
    // Update UI highlights
    document.querySelectorAll('.temp-btn').forEach(btn => {
        btn.classList.toggle('active', btn.innerText === name);
    });

    renderTemplate();
}

function renderTemplate(existingData = {}) {
    const fields = TEMPLATES[activeTemplate];
    dynamicFields.innerHTML = '';

    fields.forEach(field => {
        const group = document.createElement('div');
        group.className = 'field-group';
        group.innerHTML = `<label class="field-label">${field.label}</label>`;

        const value = existingData[field.key] || '';

        if (field.type === 'text' || field.type === 'tags') {
            group.innerHTML += `<input type="text" data-key="${field.key}" class="field-input" placeholder="${field.placeholder}" value="${value}">`;
        } else if (field.type === 'textarea') {
            group.innerHTML += `<textarea data-key="${field.key}" class="field-textarea" placeholder="${field.placeholder}" rows="4">${value}</textarea>`;
        } else if (field.type === 'list') {
            const listContainer = document.createElement('div');
            listContainer.className = 'space-y-3';
            const listValues = Array.isArray(value) ? value : ['', '', ''];
            for (let i = 0; i < field.count; i++) {
                listContainer.innerHTML += `<input type="text" data-key="${field.key}" data-index="${i}" class="field-input list-input" placeholder="${field.placeholder}${i+1}" value="${listValues[i] || ''}">`;
            }
            group.appendChild(listContainer);
        } else if (field.type === 'range') {
            group.innerHTML += `
                <div class="flex items-center gap-6">
                    <input type="range" data-key="${field.key}" min="${field.min}" max="${field.max}" value="${value || 5}" class="range-slider flex-1">
                    <span class="text-2xl font-bold w-8 text-center" id="range-val-${field.key}">${value || 5}</span>
                </div>`;
            setTimeout(() => {
                const slider = group.querySelector('input[type="range"]');
                const display = group.querySelector('span');
                slider.oninput = () => display.innerText = slider.value;
            }, 0);
        } else if (field.type === 'emoji') {
            const emojis = ['😊', '😐', '😔', '😡', '😴'];
            const selector = document.createElement('div');
            selector.className = 'emoji-selector';
            emojis.forEach(e => {
                const btn = document.createElement('div');
                btn.className = `emoji-btn ${value === e ? 'active' : ''}`;
                btn.innerText = e;
                btn.onclick = () => {
                    selector.querySelectorAll('.emoji-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    selector.dataset.value = e;
                };
                selector.appendChild(btn);
            });
            selector.dataset.key = field.key;
            selector.dataset.value = value || '';
            group.appendChild(selector);
        } else if (field.type === 'todo') {
            const container = document.createElement('div');
            container.className = 'todo-container space-y-2';
            const todos = Array.isArray(value) ? value : [{text: '', done: false}];
            
            const renderTodos = () => {
                container.innerHTML = '';
                todos.forEach((todo, idx) => {
                    const item = document.createElement('div');
                    item.className = 'todo-item';
                    item.innerHTML = `
                        <input type="checkbox" ${todo.done ? 'checked' : ''} onchange="this.parentElement.dataset.done = this.checked">
                        <input type="text" class="bg-transparent border-none outline-none flex-1" value="${todo.text}" placeholder="Add task..." oninput="this.parentElement.dataset.text = this.value">
                    `;
                    item.dataset.text = todo.text;
                    item.dataset.done = todo.done;
                    container.appendChild(item);
                });
                const addBtn = document.createElement('button');
                addBtn.className = 'text-[10px] opacity-30 hover:opacity-100 uppercase mt-2';
                addBtn.innerText = "+ Add Item";
                addBtn.onclick = () => { todos.push({text: '', done: false}); renderTodos(); };
                container.appendChild(addBtn);
            };
            renderTodos();
            container.dataset.key = field.key;
            container.className += " todo-list-field";
            group.appendChild(container);
        }

        dynamicFields.appendChild(group);
    });
}

function gatherFormData() {
    const data = {};
    const fields = dynamicFields.querySelectorAll('[data-key]');
    
    fields.forEach(field => {
        const key = field.dataset.key;
        if (field.classList.contains('list-input')) {
            if (!data[key]) data[key] = [];
            data[key][parseInt(field.dataset.index)] = field.value;
        } else if (field.classList.contains('emoji-selector')) {
            data[key] = field.dataset.value;
        } else if (field.classList.contains('todo-list-field')) {
            data[key] = Array.from(field.querySelectorAll('.todo-item')).map(item => ({
                text: item.dataset.text,
                done: item.dataset.done === 'true'
            }));
        } else {
            data[key] = field.value;
        }
    });

    return data;
}

async function saveEntry() {
    saveBtn.innerText = "Syncing...";
    saveBtn.classList.add('syncing');

    const entryData = {
        id: activeEntryId,
        date: new Date().toISOString(),
        template: activeTemplate,
        title: entryTitle.value,
        data: gatherFormData()
    };

    try {
        const response = await fetch('/api/diary/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(entryData)
        });
        const result = await response.json();
        if (result.status === 'success') {
            activeEntryId = null; // Clear active state to signal "Saved"
            entryTitle.value = '';
            selectTemplate("Custom Note");
            await fetchEntries();
            syncTime.innerText = new Date().toLocaleTimeString();
            deleteBtn.classList.add('hidden');
        }
    } catch (err) {
        console.error("Save failed", err);
    } finally {
        saveBtn.innerText = "Save Note";
        saveBtn.classList.remove('syncing');
    }
}

async function loadEntry(id) {
    const entry = entries.find(e => e.id === id);
    if (!entry) return;

    activeEntryId = entry.id;
    activeTemplate = entry.template;
    entryTitle.value = entry.title;
    activeTemplateLabel.innerText = entry.template;
    
    switchTab('journal');
    selectTemplate(entry.template);
    renderTemplate(entry.data);
    deleteBtn.classList.remove('hidden');
    renderEntriesList();
}

async function deleteEntry() {
    if (!activeEntryId || !confirm("Erase this memory forever?")) return;
    try {
        await fetch('/api/diary/delete/' + activeEntryId, {
            method: 'DELETE'
        });
        activeEntryId = null;
        entryTitle.value = '';
        selectTemplate("Custom Note");
        await fetchEntries();
        deleteBtn.classList.add('hidden');
    } catch (err) {
        console.error("Delete failed", err);
    }
}

// --- CALENDAR ---

function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listWeek'
        },
        events: mapEntriesToEvents(),
        eventClick: (info) => loadEntry(info.event.id),
        height: '100%',
        themeSystem: 'standard'
    });
    calendar.render();
}

function mapEntriesToEvents() {
    const colors = {
        "Daily Reflection": "#a855f7",
        "Productivity": "#10b981",
        "Mood Tracker": "#f59e0b",
        "Weekly Growth": "#3b82f6",
        "Future Vision": "#ec4899"
    };

    return entries.map(e => ({
        id: e.id,
        title: e.title || e.template,
        start: e.date,
        color: colors[e.template] || '#fff'
    }));
}

// --- UTILS ---

function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById('tab-' + tab).classList.add('active');

    document.getElementById('view-journal').classList.toggle('hidden', tab !== 'journal');
    document.getElementById('view-calendar').classList.toggle('hidden', tab !== 'calendar');

    if (tab === 'calendar' && calendar) {
        setTimeout(() => calendar.updateSize(), 10);
    }
}

function setupReminders() {
    const setBtn = document.getElementById('set-reminder');
    const timeInput = document.getElementById('reminder-time');
    const reqBtn = document.getElementById('request-notif-btn');

    reqBtn.onclick = () => {
        if (!("Notification" in window)) return alert("Not supported");
        Notification.requestPermission().then(permission => {
            if (permission === "granted") {
                new Notification("Notifications Enabled!", { body: "Project Peace will now remind you to journal." });
            }
        });
    };

    setBtn.onclick = () => {
        if (Notification.permission !== "granted") {
            alert("Please enable notifications using the button below first.");
            return;
        }
        const timeStr = timeInput.value;
        if (!timeStr) return;
        
        localStorage.setItem('diary_reminder', timeStr);
        alert(`Reminder set for ${timeStr}`);
        startReminderCheck();
    };

    const saved = localStorage.getItem('diary_reminder');
    if (saved) {
        timeInput.value = saved;
        startReminderCheck();
    }
}

function startReminderCheck() {
    setInterval(() => {
        const setTime = localStorage.getItem('diary_reminder');
        const now = new Date();
        const nowStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
        
        if (setTime === nowStr && !window.remindedToday) {
            new Notification("Project Peace: Journal Time! 🌿", {
                body: "Take a moment to reflect on your day.",
                icon: "/static/img/kai_icon.png"
            });
            window.remindedToday = true;
            setTimeout(() => window.remindedToday = false, 61000);
        }
    }, 30000);
}

// --- AMBIENT SOUND ---
function setupAmbientSound() {
    const video = document.getElementById('diary-bg-video');
    const audio = document.getElementById('bg-music');

    // Setup initial state
    video.muted = true; 
    audio.volume = 0.25; // User requested 25% volume
    audio.muted = true; // MUST start muted for autoplay compliance

    // Browsers block auto-unmute unless user has interacted. 
    const startAudio = () => {
        audio.muted = false;
        audio.play().catch(err => {
            console.warn("Audio play failed on gesture:", err);
        });
    };

    document.addEventListener('click', startAudio, { once: true });
    document.addEventListener('keydown', startAudio, { once: true });
}

// --- EVENTS ---
setupAmbientSound();
document.getElementById('new-entry-btn').onclick = () => {
    activeEntryId = null;
    entryTitle.value = '';
    selectTemplate("Custom Note");
    deleteBtn.classList.add('hidden');
    renderEntriesList();
};

saveBtn.onclick = saveEntry;
deleteBtn.onclick = deleteEntry;
document.getElementById('search-entries').oninput = (e) => {
    // Basic filter
    const term = e.target.value.toLowerCase();
    document.querySelectorAll('.entry-item').forEach(item => {
        const title = item.querySelector('.snippet-title').innerText.toLowerCase();
        item.style.display = title.includes(term) ? 'block' : 'none';
    });
};
