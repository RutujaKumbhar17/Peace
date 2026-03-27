from flask import Flask, render_template, url_for, request, redirect
from flask_socketio import SocketIO, emit
from camera_utils import analyze_emotion_from_frame, LOG_FILE, BASE_DIR
import pyttsx3 
import os 
import time
import glob 
import csv
import json
import google.generativeai as genai
from config import apikey
import webbrowser
from collections import deque

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['STATIC_URL_PATH'] = '/static'
app.config['SECRET_KEY'] = 'kai_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

genai.configure(api_key=apikey)

# ... (Keep existing Safety Settings & System Instructions unchanged) ...
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

system_instruction = (
    "You are Kai, a helpful, charming, and empathetic AI video companion. "
    "Your responses should be conversational, concise (under 2 sentences), and natural. "
    "Act like a real person present with the user. "
    "\n\n"
    "### EMOTION HANDLING RULES ###\n"
    "1. You will receive a hidden tag like '[USER STATE: Happy]' at the start of messages.\n"
    "2. **INTERNAL USE ONLY:** Use this tag to adjust your tone (e.g., be softer if Sad, energetic if Happy).\n"
    "3. **DO NOT** mention the tag or the user's emotion in your response unless explicitly asked.\n"
    "   - INCORRECT: '[USER STATE: Sad] Oh, I see you are sad. How can I help?'\n"
    "   - CORRECT: 'I'm here for you. What's on your mind?'\n"
    "4. **EXCEPTION:** If the user asks 'How do I look?' or 'What is my mood?', THEN you may answer using the tag."
)

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    system_instruction=system_instruction,
    safety_settings=safety_settings
)

# Persistent file for chat history
CHAT_LOG_FILE = os.path.join(BASE_DIR, 'logs', 'chat_history.json')

# In-memory stores
conversation_history = {}
emotion_history = {}

AUDIO_DIR = os.path.join(app.root_path, 'static', 'audio')
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)

# --- ROUTES ---

@app.route('/')
def landing():
    """Render the Intro/Landing Page"""
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the Login Page"""
    if request.method == 'POST':
        # Simple login logic: redirect to home
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/home')
def home():
    """Render the New Navigation/Home Page"""
    return render_template('home.html')

@app.route('/chat')
def chat():
    """Render the Dedicated Chat Section"""
    return render_template('chat.html')

@app.route('/diary')
def diary():
    """Render the My Diary Section"""
    return render_template('diary.html')

@app.route('/dashboard')
def dashboard():
    """Render the Dashboard Section"""
    return render_template('dashboard.html')

@app.route('/companion')
def companion():
    """Render the Main Kai Interface (Previously Index)"""
    return render_template('call.html')

@app.route('/api/mood-stats')
def mood_stats():
    """Process emotion logs and return aggregated stats for the dashboard"""
    if not os.path.exists(LOG_FILE):
        return json.dumps({"status": "no_data", "top_emotions": []})
    
    try:
        emotion_counts = {}
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 4:
                    emotion = row[3]
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Sort and get top 3
        sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
        top_3 = [{"emotion": e, "count": c} for e, c in sorted_emotions[:3]]
        
        return json.dumps({
            "status": "success",
            "top_emotions": top_3,
            "total_logs": sum(emotion_counts.values())
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# --- HELPER FUNCTIONS ---
# ... (Keep all existing helper functions: cleanup_audio_folder, generate_tts_audio, process_browser_command, load_emotion_logs, save_chat_log, load_chat_log, calculate_weighted_emotion UNCHANGED) ...

def cleanup_audio_folder():
    try:
        current_time = time.time()
        files = glob.glob(os.path.join(AUDIO_DIR, "*"))
        for f in files:
            if f.endswith(".mp3") or f.endswith(".wav"):
                if current_time - os.path.getctime(f) > 30: 
                    os.remove(f)
    except Exception as e:
        print(f"Cleanup Error: {e}")

def generate_tts_audio(text):
    cleanup_audio_folder()
    filename = f"response_{int(time.time())}.wav"
    audio_path = os.path.join(AUDIO_DIR, filename)
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 175) 
        engine.save_to_file(text, audio_path)
        engine.runAndWait()
        return url_for('static', filename=f'audio/{filename}')
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def process_browser_command(text):
    lower_text = text.lower()
    sites = {
        "open youtube": "https://www.youtube.com",
        "open google": "https://www.google.com",
        "open facebook": "https://www.facebook.com",
        "open instagram": "https://www.instagram.com",
        "open twitter": "https://twitter.com",
        "open github": "https://github.com",
        "open stackoverflow": "https://stackoverflow.com",
        "open reddit": "https://www.reddit.com",
        "open linkedin": "https://www.linkedin.com"
    }
    for command, url in sites.items():
        if command in lower_text:
            webbrowser.open(url)
            return f"Opening {command.replace('open ', '').title()}."
    if "search" in lower_text and "google" in lower_text:
        query = lower_text.replace("search", "").replace("on google", "").replace("for", "").strip()
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching Google for {query}."
    if "play" in lower_text and "youtube" in lower_text:
        query = lower_text.replace("play", "").replace("on youtube", "").strip()
        if query:
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"Playing {query} on YouTube."
    return None

def load_emotion_logs():
    restored_data = []
    if not os.path.exists(LOG_FILE):
        return restored_data
    try:
        current_time = time.time()
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            next(reader, None) # Skip header
            rows = list(reader)
            for row in rows:
                try:
                    timestamp = float(row[0])
                    if current_time - timestamp <= 60:
                        emotion = row[3]
                        score = float(row[4])
                        restored_data.append((timestamp, emotion, score))
                except:
                    continue
    except Exception as e:
        print(f"Error restoring emotion logs: {e}")
    return restored_data

def save_chat_log(history_list):
    try:
        to_save = list(history_list)[-20:] 
        with open(CHAT_LOG_FILE, 'w') as f:
            json.dump(to_save, f)
    except Exception as e:
        print(f"Error saving chat log: {e}")

def load_chat_log():
    try:
        if os.path.exists(CHAT_LOG_FILE):
            with open(CHAT_LOG_FILE, 'r') as f:
                return deque(json.load(f), maxlen=20)
    except Exception as e:
        print(f"Error loading chat log: {e}")
    return deque(maxlen=20)

def calculate_weighted_emotion(sid):
    if sid not in emotion_history or not emotion_history[sid]:
        return "Neutral"

    now = time.time()
    weighted_scores = {} 
    for timestamp, emotion, score in emotion_history[sid]:
        age = now - timestamp
        if age > 60: continue
        time_weight = 1.0 / (1.0 + (age / 5.0))
        frame_points = score * time_weight
        weighted_scores[emotion] = weighted_scores.get(emotion, 0.0) + frame_points

    if not weighted_scores: return "Neutral"
    return max(weighted_scores, key=weighted_scores.get)

# --- SOCKET EVENTS ---
# ... (Keep existing socket events UNCHANGED) ...

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    print(f"User connected: {sid}")
    conversation_history[sid] = load_chat_log()
    recent_logs = load_emotion_logs()
    emotion_history[sid] = deque(recent_logs)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in conversation_history: del conversation_history[sid]
    if sid in emotion_history: del emotion_history[sid]
    print(f"User disconnected: {sid}")

@socketio.on('video_frame')
def handle_frame(data_url):
    sid = request.sid
    result = analyze_emotion_from_frame(data_url)
    if result:
        emotion = result['emotion']
        score = result['score']
        if sid not in emotion_history:
             emotion_history[sid] = deque()
        emotion_history[sid].append((time.time(), emotion, score))
        while emotion_history[sid] and emotion_history[sid][0][0] < time.time() - 60:
            emotion_history[sid].popleft()
        emit('ai_response', {'emotion': emotion, 'audio_url': None}) 

@socketio.on('chat_message')
def handle_chat(data):
    sid = request.sid
    user_msg = data.get('message', '')
    if user_msg.strip():
        print(f"User ({sid}): {user_msg}")
        command_reply = process_browser_command(user_msg)
        if command_reply:
            ai_reply = command_reply
        else:
            if sid not in conversation_history:
                conversation_history[sid] = load_chat_log()
            current_mood = calculate_weighted_emotion(sid)
            system_context = f"[USER STATE: {current_mood}]. "
            full_prompt = system_context + user_msg
            current_history = list(conversation_history[sid])
            try:
                chat = model.start_chat(history=current_history)
                response = chat.send_message(full_prompt)
                ai_reply = response.text
                conversation_history[sid].append({'role': 'user', 'parts': [user_msg]})
                conversation_history[sid].append({'role': 'model', 'parts': [ai_reply]})
                save_chat_log(conversation_history[sid])
            except Exception as e:
                print(f"Gemini Error: {e}")
                ai_reply = "I'm having trouble thinking right now."
        emit('chat_response', {'response': ai_reply})
        audio_url = generate_tts_audio(ai_reply)
        emit('ai_response', {'emotion': 'neutral', 'audio_url': audio_url})

if __name__ == '__main__':
    print("Starting Kai Server (Optimized & Persistent)...")
    socketio.run(app, debug=True, port=5001)