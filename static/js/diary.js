// diary.js - Logic for My Diary Module

// --- STATE MANAGEMENT ---
let notes = JSON.parse(localStorage.getItem('kai_diary_notes')) || [];
let activeNoteId = null;
let saveTimeout = null;
let sortAscending = false;

// --- DOM ELEMENTS ---
const noteList = document.getElementById('note-list');
const newNoteBtn = document.getElementById('new-note-btn');
const searchInput = document.getElementById('search-input');
const sortToggle = document.getElementById('sort-toggle');
const editorView = document.getElementById('editor-view');
const emptyState = document.getElementById('empty-state');
const richEditor = document.getElementById('rich-editor');
const noteTitle = document.getElementById('note-title');
const deleteNoteBtn = document.getElementById('delete-note-btn');
const saveStatus = document.getElementById('save-status');
const toolbarBtns = document.querySelectorAll('.toolbar-btn[data-command]');
const tagInput = document.getElementById('tag-input');
const tagContainer = document.getElementById('note-tags');

// --- INITIALIZATION ---
function init() {
    renderNoteList();
    setupEventListeners();
}

// --- UTILS ---
function timeSince(date) {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    if (seconds < 60) return "Just now";
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return Math.floor(seconds) + " seconds ago";
}

function saveToLocalStorage() {
    localStorage.setItem('kai_diary_notes', JSON.stringify(notes));
}

// --- CORE LOGIC ---
function renderNoteList() {
    const searchTerm = searchInput.value.toLowerCase();
    let filteredNotes = notes.filter(n => 
        n.title.toLowerCase().includes(searchTerm) || 
        n.content.toLowerCase().includes(searchTerm) ||
        (n.tags && n.tags.some(t => t.toLowerCase().includes(searchTerm)))
    );

    // Sort
    filteredNotes.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return sortAscending ? dateA - dateB : dateB - dateA;
    });

    noteList.innerHTML = '';
    
    if (filteredNotes.length === 0) {
        noteList.innerHTML = '<div style="padding:40px; text-align:center; color:#444;">No notes found.</div>';
    }

    filteredNotes.forEach(note => {
        const snippet = document.createElement('div');
        snippet.className = `note-snippet ${note.id === activeNoteId ? 'active' : ''}`;
        snippet.innerHTML = `
            <div class="snippet-title">${note.title || 'Untitled Note'}</div>
            <div class="snippet-meta">${timeSince(note.date)}</div>
            <div class="snippet-preview">${note.content.replace(/<[^>]*>/g, '') || 'Empty...'}</div>
        `;
        snippet.onclick = () => selectNote(note.id);
        noteList.appendChild(snippet);
    });
}

function createNewNote() {
    const newNote = {
        id: 'note_' + Date.now(),
        title: '',
        content: '',
        date: new Date().toISOString(),
        tags: []
    };
    notes.unshift(newNote);
    saveToLocalStorage();
    activeNoteId = newNote.id;
    renderNoteList();
    selectNote(newNote.id);
}

function selectNote(id) {
    if (activeNoteId === id) return; // Already selected
    
    // Add fade-out transition
    editorView.style.opacity = '0';
    
    setTimeout(() => {
        activeNoteId = id;
        const note = notes.find(n => n.id === id);
        if (!note) return;

        // UI Updates
        document.querySelectorAll('.note-snippet').forEach(s => s.classList.remove('active'));
        renderNoteList(); 

        emptyState.style.display = 'none';
        editorView.style.display = 'flex';
        
        noteTitle.value = note.title;
        richEditor.innerHTML = note.content;
        renderTags(note.tags);
        
        // Fade back in
        editorView.style.opacity = '1';
        saveStatus.innerText = 'Saved';
    }, 150);
}

function updateNote() {
    if (!activeNoteId) return;
    const noteIndex = notes.findIndex(n => n.id === activeNoteId);
    if (noteIndex === -1) return;

    notes[noteIndex].title = noteTitle.value;
    notes[noteIndex].content = richEditor.innerHTML;
    // We update the date only if they actually changed something significant?
    // Maybe not on every keystroke to keep it stable.
    
    saveStatus.innerText = 'Saving...';
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        saveToLocalStorage();
        saveStatus.innerText = 'Saved';
        renderNoteList();
    }, 1000);
}

function deleteNote() {
    if (!activeNoteId) return;
    if (confirm("Are you sure you want to delete this note?")) {
        notes = notes.filter(n => n.id !== activeNoteId);
        saveToLocalStorage();
        activeNoteId = null;
        editorView.style.display = 'none';
        emptyState.style.display = 'flex';
        renderNoteList();
    }
}

function renderTags(tags) {
    const tagElements = tagContainer.querySelectorAll('.tag');
    tagElements.forEach(e => e.remove());
    
    tags.forEach(tag => {
        const tagEl = document.createElement('div');
        tagEl.className = 'tag';
        tagEl.style.cssText = 'background:#333; border-radius:5px; padding:3px 8px; font-size:0.75rem; color:#008069; display:flex; align-items:center; gap:5px;';
        tagEl.innerHTML = `${tag} <i class="fas fa-times" style="cursor:pointer; color:#888;"></i>`;
        tagEl.querySelector('i').onclick = () => removeTag(tag);
        tagContainer.insertBefore(tagEl, document.getElementById('tag-input-container'));
    });
}

function addTag(tag) {
    if (!activeNoteId || !tag.trim()) return;
    const note = notes.find(n => n.id === activeNoteId);
    if (!note) return;
    if (!note.tags.includes(tag)) {
        note.tags.push(tag);
        saveToLocalStorage();
        renderTags(note.tags);
    }
    tagInput.value = '';
}

function removeTag(tag) {
    const note = notes.find(n => n.id === activeNoteId);
    if (!note) return;
    note.tags = note.tags.filter(t => t !== tag);
    saveToLocalStorage();
    renderTags(note.tags);
}

// --- EVENT LISTENERS ---
function setupEventListeners() {
    newNoteBtn.onclick = createNewNote;
    deleteNoteBtn.onclick = deleteNote;
    
    searchInput.oninput = renderNoteList;
    
    sortToggle.onclick = () => {
        sortAscending = !sortAscending;
        sortToggle.className = sortAscending ? 'fas fa-sort-amount-up' : 'fas fa-sort-amount-down';
        renderNoteList();
    };

    noteTitle.oninput = updateNote;
    richEditor.oninput = updateNote;

    tagInput.onkeypress = (e) => {
        if (e.key === 'Enter') addTag(tagInput.value);
    };

    // Toolbar logic (Modern approach: Use selection)
    toolbarBtns.forEach(btn => {
        btn.onmousedown = (e) => {
            e.preventDefault(); 
            const command = btn.getAttribute('data-command');
            
            // Expert Tip: Add specific styling to the active button
            btn.classList.add('active');
            setTimeout(() => btn.classList.remove('active'), 200);

            if (command === 'createLink') {
                const url = prompt("Enter the URL:");
                if (url) document.execCommand(command, false, url);
            } else if (command === 'formatBlock') {
                document.execCommand(command, false, '<blockquote>');
            } else {
                document.execCommand(command, false, null);
            }
            
            richEditor.focus();
            updateNote();
        };
    });
}

// --- START APP ---
init();
