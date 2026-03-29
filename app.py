from flask import Flask, render_template, url_for, request, redirect, send_from_directory
from flask_socketio import SocketIO, emit
from camera_utils import analyze_emotion_from_frame, LOG_FILE, BASE_DIR
import pyttsx3 
import os 
import time
import glob 
import csv
import json
from google import genai
from config import apikey, model_name
import webbrowser
import sqlite3
from collections import deque
from datetime import datetime, timedelta
import requests

DB_PATH = os.path.join(BASE_DIR, 'logs', 'peace.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diary_entries (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                template_type TEXT NOT NULL,
                title TEXT,
                content_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

init_db()

app = Flask(__name__)
app.config['STATIC_FOLDER'] = 'static'
app.config['STATIC_URL_PATH'] = '/static'
app.config['SECRET_KEY'] = 'kai_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- OpenRouter (KAI) Config ---
OPENROUTER_API_KEY = ""
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# (Gemini Client left for reference, but logic is replaced)
client = genai.Client(api_key=apikey)

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

# (Deprecated legacy model logic removed)

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

@app.route('/api/dashboard-data')
def dashboard_data():
    """Aggregated data for the new Bento Dashboard"""
    data = {
        "mood_distribution": {},
        "glow_gallery": [],
        "streak": 0,
        "reflection": "Always find something to be grateful for."
    }
    
    # 1. Mood Distribution & Glow Gallery (from Logs)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                reader = csv.reader(f)
                next(reader, None) # Skip header
                logs = list(reader)
                
                dates = set()
                for row in logs:
                    if len(row) >= 5:
                        emotion = row[3]
                        score = float(row[4])
                        date = row[1]
                        dates.add(date)
                        
                        # Distribution
                        data["mood_distribution"][emotion] = data["mood_distribution"].get(emotion, 0) + 1
                        
                        # Distribution
                        data["mood_distribution"][emotion] = data["mood_distribution"].get(emotion, 0) + 1
                        
                        # Note: We no longer append text logs to glow_gallery here 
                        # to keep the gallery strictly visual.
                
                # 2. Weekly Mood Data (for Emotional Balance)
                weekly_moods = {"labels": [], "scores": []}
                recent_logs = logs[-14:] # Get last 14 entries for better trend
                for row in recent_logs:
                    if len(row) >= 5:
                        # Simplify timestamp for display
                        t = datetime.fromtimestamp(float(row[0])).strftime("%H:%M")
                        weekly_moods["labels"].append(t)
                        weekly_moods["scores"].append(round(float(row[4]) * 100, 1))
                data["weekly_moods"] = weekly_moods

                # 3. Calendar Events (Days Logged)
                data["calendar_events"] = [{"title": "Sanctuary Visited", "start": d, "display": "background", "color": "#967BB6"} for d in sorted(list(dates))]

                # 4. Sprout Streak Logic
                if dates:
                    current_streak = 0
                    check_date = datetime.now().date()
                    sorted_dates = sorted(list(dates), reverse=True)
                    last_log_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d").date()
                    
                    if last_log_date < check_date - timedelta(days=1):
                         current_streak = 0
                    else:
                        for d_str in sorted_dates:
                            d = datetime.strptime(d_str, "%Y-%m-%d").date()
                            if d == last_log_date:
                                current_streak += 1
                                last_log_date -= timedelta(days=1)
                            else:
                                break
                    data["streak"] = current_streak
        except Exception as e:
            print(f"Error processing logs for dashboard: {e}")

    # 3. Reflection (Random Diary Snippet)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT content_json FROM diary_entries ORDER BY RANDOM() LIMIT 5')
            rows = cursor.fetchall()
            for row in rows:
                content = json.loads(row['content_json'])
                # Look for gratitude-like sentences
                for key, val in content.items():
                    if isinstance(val, str) and ("grateful" in val.lower() or "happy" in val.lower() or "good" in val.lower()):
                        data["reflection"] = val
                        break
                if data["reflection"] != "Always find something to be grateful for.":
                    break
    except Exception as e:
        print(f"Error fetching reflection: {e}")

    # 4. Joy Gallery Images (Legacy static/joy_gallery + New captured_frames/happy)
    JOY_DIR = os.path.join(app.root_path, 'static', 'joy_gallery')
    if os.path.exists(JOY_DIR):
        images = glob.glob(os.path.join(JOY_DIR, "*"))
        for img in images:
            if img.lower().endswith(('.png', '.jpg', '.jpeg')):
                data["glow_gallery"].append({
                    "type": "image",
                    "url": url_for('static', filename=f'joy_gallery/{os.path.basename(img)}')
                })
    
    # 5. Real Happy Captures (Faceography)
    CAPTURES_DIR = os.path.join(BASE_DIR, 'captured_frames')
    if os.path.exists(CAPTURES_DIR):
        # Find all files with "happy" in the name
        happy_files = glob.glob(os.path.join(CAPTURES_DIR, "*happy*"))
        # Sort by most recent
        happy_files.sort(key=os.path.getmtime, reverse=True)
        for img_path in happy_files[:10]: # Limit to 10
            filename = os.path.basename(img_path)
            # Use our new /captures/ route
            data["glow_gallery"].append({
                "type": "capture",
                "url": f"/captures/{filename}",
                "date": time.strftime("%b %d", time.localtime(os.path.getmtime(img_path)))
            })

    # 6. Fallback/Inspiration Gallery (if empty)
    if not data["glow_gallery"]:
        placeholders = [
            {"url": "https://images.unsplash.com/photo-1518199266791-5375a02c9b24?auto=format&fit=crop&q=80&w=400", "date": "Ocean Peace"},
            {"url": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&q=80&w=400", "date": "Forest Whisper"},
            {"url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&q=80&w=400", "date": "Golden Valley"},
            {"url": "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&q=80&w=400", "date": "Alpine Calm"},
            {"url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&q=80&w=400", "date": "Sunlit Woods"}
        ]
        for p in placeholders:
            data["glow_gallery"].append({
                "type": "placeholder",
                "url": p["url"],
                "date": p["date"]
            })

    # 7. AI Activity Suggestions
    top_mood = "Neutral"
    if data["mood_distribution"]:
        top_mood = max(data["mood_distribution"], key=data["mood_distribution"].get)
    
    data["top_mood"] = top_mood
    data["activity_suggestions"] = []
    
    # Calculate True Streak (Consecutive Days)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                reader = csv.reader(f)
                next(reader, None)
                dates = sorted(list(set(row[1] for row in reader)), reverse=True)
                if dates:
                    current_streak = 0
                    check_date = datetime.now().date()
                    
                    # If no log today, check from yesterday
                    last_log_date = datetime.strptime(dates[0], "%Y-%m-%d").date()
                    if last_log_date < check_date - timedelta(days=1):
                         current_streak = 0
                    else:
                        for d_str in dates:
                            d = datetime.strptime(d_str, "%Y-%m-%d").date()
                            if d == last_log_date:
                                current_streak += 1
                                last_log_date -= timedelta(days=1)
                            else:
                                break
                    data["streak"] = current_streak
        except Exception as e:
            print(f"Streak Error: {e}")

    try:
        suggestion_prompt = (
            f"The user, Rutuja, has been feeling '{top_mood}' lately. "
            f"As her soulful AI companion, suggest 3 fresh, poetic, and modern mindfulness activities. "
            f"Avoid clichés. Use evocative language (e.g., 'sip the silence', 'trace the grain of the day'). "
            f"Keep each under 10 words. Return ONLY a JSON list of strings."
        )
        response = client.models.generate_content(
            model=model_name,
            contents=suggestion_prompt,
            config={'response_mime_type': 'application/json'}
        )
        data["activity_suggestions"] = json.loads(response.text)
    except Exception as e:
        print(f"Error generating AI suggestions: {e}")
        # Fallback
        fallbacks = {
            "happy": ["Share your joy with a friend", "Write a gratitude note", "Listen to upbeat music"],
            "sad": ["Gentle stretching", "Deep breathing", "Sipping warm tea"],
            "angry": ["Cool water on face", "Quick walk outside", "Counting to 10 slowly"]
        }
        data["activity_suggestions"] = fallbacks.get(top_mood.lower(), ["Deep breath", "Mindful moment", "Stretch"])

    return json.dumps(data)

def get_kai_response(messages):
    """Call OpenRouter API to get a response from Kai"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"model": OPENROUTER_MODEL, "messages": messages}
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=10)
        res_json = response.json()
        if 'choices' in res_json:
            return res_json['choices'][0]['message']['content'].strip()
        print(f"OpenRouter Error: {res_json}")
        return "I'm having trouble thinking right now."
    except Exception as e:
        print(f"Request Error: {e}")
        return "I'm having trouble thinking right now."

@app.route('/api/kai-insight')
def kai_insight():
    """Generate a personalized 'Seen' message from Kai based on user context"""
    history = load_chat_log()
    last_user_msg = "Nothing yet"
    for turn in reversed(list(history)):
        if turn['role'] == 'user':
            last_user_msg = turn['parts'][0]
            break
            
    # Get last emotion
    last_mood = "Neutral"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            if len(rows) > 1:
                last_mood = rows[-1][3]

    insight_prompt = (
        f"User context: Last mood observed: {last_mood}. Last thing they said: '{last_user_msg}'. "
        f"As Rutuja's soulful companion, write a 1-sentence, 'fresh' and poetic 'Seen' insight. "
        f"Make it feel like a whisper of wisdom or a warm embrace. Avoid overused therapy-speak. "
        f"Keep it under 18 words and deeply personal."
    )
    
    messages = [
        {"role": "system", "content": "You are Kai, Rutuja's soulful AI companion. Be poetic and fresh."},
        {"role": "user", "content": insight_prompt}
    ]
    
    insight_text = get_kai_response(messages)
    return json.dumps({"insight": insight_text})


@app.route('/captures/<path:filename>')
def serve_capture(filename):
    """Serve images from the captured_frames directory"""
    CAPTURES_DIR = os.path.join(BASE_DIR, 'captured_frames')
    return send_from_directory(CAPTURES_DIR, filename)


# --- DIARY API ---

@app.route('/api/diary/save', methods=['POST'])
def save_diary_entry():
    data = request.json
    if not data:
        return json.dumps({"status": "error", "message": "No data provided"}), 400
    
    entry_id = data.get('id')
    date = data.get('date')
    template = data.get('template')
    title = data.get('title', 'Untitled Entry')
    content = json.dumps(data.get('data', {}))
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if entry_id:
                # Update existing
                cursor.execute('''
                    INSERT OR REPLACE INTO diary_entries (id, date, template_type, title, content_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (entry_id, date, template, title, content))
            else:
                # New entry
                import uuid
                entry_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO diary_entries (id, date, template_type, title, content_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (entry_id, date, template, title, content))
            conn.commit()
        return json.dumps({"status": "success", "id": entry_id})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}), 500

@app.route('/api/diary/entries')
def get_diary_entries():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM diary_entries ORDER BY date DESC')
            rows = cursor.fetchall()
            entries = []
            for row in rows:
                entries.append({
                    "id": row['id'],
                    "date": row['date'],
                    "template": row['template_type'],
                    "title": row['title'],
                    "data": json.loads(row['content_json'])
                })
        return json.dumps({"status": "success", "entries": entries})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}), 500

@app.route('/api/diary/delete/<id>', methods=['DELETE'])
def delete_diary_entry(id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM diary_entries WHERE id = ?', (id,))
            conn.commit()
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}), 500

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
            
            # Format Context History (Remember last 6 turns = 12 messages)
            messages = [{"role": "system", "content": system_instruction.replace("[USER STATE: Happy]", f"[USER STATE: {current_mood}]")}]
            
            # Convert existing parts history to OpenAI format
            # We take the last 12 entries (6 turns)
            raw_history = list(conversation_history[sid])[-12:] 
            for turn in raw_history:
                role = "user" if turn['role'] == 'user' else "assistant"
                messages.append({"role": role, "content": turn['parts'][0]})
            
            # Add current message
            # The current current_mood is already in the system check, but we can also tag it here if needed
            messages.append({"role": "user", "content": f"[USER STATE: {current_mood}] {user_msg}"})
            
            try:
                print(f"[OPENROUTER] Sending context (6 turns): {user_msg}")
                ai_reply = get_kai_response(messages)
                print(f"[OPENROUTER] Received: {ai_reply}")
                
                # Update Persistence Store
                conversation_history[sid].append({'role': 'user', 'parts': [user_msg]})
                conversation_history[sid].append({'role': 'assistant', 'parts': [ai_reply]})
                save_chat_log(conversation_history[sid])
            except Exception as e:
                print(f"OpenRouter Error (General): {e}")
                ai_reply = "I'm having trouble thinking right now."
        
        print(f"[SOCKET] Emitting chat_response...")
        emit('chat_response', {'response': ai_reply})
        
        print(f"[TTS] Generating audio...")
        audio_url = generate_tts_audio(ai_reply)
        emit('ai_response', {'emotion': 'neutral', 'audio_url': audio_url})

if __name__ == '__main__':
    print("Starting Kai Server (Optimized & Persistent)...")
    socketio.run(app, debug=True, port=5002)