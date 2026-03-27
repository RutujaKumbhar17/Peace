// dashboard.js - Logic for Dynamic Dashboard

document.addEventListener('DOMContentLoaded', () => {
    loadDiaryStats();
    loadMoodStats();
});

function loadDiaryStats() {
    const rawNotes = localStorage.getItem('kai_diary_notes');
    const notes = rawNotes ? JSON.parse(rawNotes) : [];
    
    // Update Count
    const countEl = document.getElementById('diary-count');
    if (countEl) countEl.innerText = notes.length;

    // Update Recent Preview
    const previewContainer = document.getElementById('recent-diary-preview');
    if (previewContainer) {
        if (notes.length === 0) {
            previewContainer.innerHTML = '<p class="empty-dashboard-state">No entries yet.</p>';
        } else {
            const last3 = notes.slice(0, 3);
            let html = '<ul class="recent-diary-list">';
            last3.forEach(note => {
                const dateStr = new Date(note.date).toLocaleDateString();
                html += `
                    <li class="recent-diary-item">
                        <span>${note.title || 'Untitled'}</span>
                        <span>${dateStr}</span>
                    </li>
                `;
            });
            html += '</ul>';
            previewContainer.innerHTML = html;
        }
    }

    // Update Last Active
    const lastActiveEl = document.getElementById('last-active');
    if (lastActiveEl && notes.length > 0) {
        lastActiveEl.innerText = timeSince(notes[0].date);
    }
}

async function loadMoodStats() {
    try {
        const response = await fetch('/api/mood-stats');
        const data = await response.json();
        
        if (data.status === 'success') {
            const topMoodEl = document.getElementById('top-mood');
            if (topMoodEl && data.top_emotions.length > 0) {
                topMoodEl.innerText = data.top_emotions[0].emotion;
            }

            const barsContainer = document.getElementById('mood-bars');
            if (barsContainer) {
                barsContainer.innerHTML = '';
                const maxCount = Math.max(...data.top_emotions.map(e => e.count));
                
                data.top_emotions.forEach(e => {
                    const height = (e.count / maxCount) * 100;
                    const bar = document.createElement('div');
                    bar.className = 'mood-bar';
                    bar.style.height = height + '%';
                    bar.innerHTML = `<span>${e.emotion}</span>`;
                    barsContainer.appendChild(bar);
                });
            }
        }
    } catch (e) {
        console.error("Error loading mood stats:", e);
    }
}

// Reuse timeSince from diary logic if possible, or redefine simply
function timeSince(date) {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    if (seconds < 60) return "Just now";
    let interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " mins ago";
    return "Recently";
}
