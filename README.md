# Kai The Companion: An Emotionally Intelligent 3D AI Video Companion

**Kai The Companion** is a sophisticated, therapy-inspired AI companion designed to provide real-time, empathetic interaction through video and text. By leveraging computer vision and natural language processing, Kai detects user emotions via facial expressions and adapts its conversational tone to offer a personalized wellness experience.

## 🚀 Key Features

* **Real-time Emotion Detection:** Uses computer vision models to analyze facial expressions and map them to emotions such as Happy, Sad, Angry, and Fear.
* **Dynamic 3D Avatar:** Features a high-fidelity 3D avatar with lip-syncing and mood-based animations.
* **Adaptive Conversational AI:** Powered by Google's Gemini models, Kai receives emotional context tags to adjust its tone.
* **Smart Browser Commands:** Capability to search Google or play YouTube videos via voice/text commands.

---

## 🏗️ Project Architectures

### **1. System Architecture**

This diagram uses high-contrast styling with **thick black connectors** to ensure full visibility of the client-to-backend pipeline.

```mermaid
graph TD
    %% Global Styles and Line Thickness
    linkStyle default stroke:#87CEEB,stroke-width:3px;
    classDef user fill:#ffffff,stroke:#000000,stroke-width:3px,color:#000000;
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:3px,color:#000000;
    classDef backend fill:#f3e5f5,stroke:#4a148c,stroke-width:3px,color:#000000;
    classDef storage fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000000;
    

    User((User Interaction)):::user
    
    subgraph Frontend_Client [Frontend: Client Side]
        UI[Main UI / Chat Window]
        Cam[Camera Capture Feed]
        AV[3D Avatar Rendering]
    end
    class Frontend_Client frontend
    
    subgraph Backend_Server [Backend: Python Flask Server]
        Srv[Flask-SocketIO App]
        CV_Engine[Emotion Analysis Engine]
        AI_Brain[Gemini LLM Integration]
        TTS_Engine[Speech Synthesis]
    end
    class Backend_Server backend

    subgraph Data_Storage [Data Logs]
        Hist[(Chat History JSON)]
        EmoteLogs[(Emotion CSV Logs)]
    end
    class Data_Storage storage

    %% Connections with specific visibility
    User ==>|Visual Expression| Cam
    Cam ==>|Base64 Image Frame| Srv
    Srv ==>|Raw Frame| CV_Engine
    CV_Engine ==>|Logged Emotion| EmoteLogs
    
    User ==>|Text Message| UI
    UI ==>|Socket Event| Srv
    
    EmoteLogs ==>|Mood Context| AI_Brain
    Srv ==>|Prompt Ingestion| AI_Brain
    
    AI_Brain ==>|Text Content| Hist
    AI_Brain ==>|Response String| TTS_Engine
    TTS_Engine ==>|Generated Audio URL| AV
    AV ==>|Voice & LipSync| User

```

### **2. Detailed Data Flow (DFD)**

The sequence below features participating blocks and participant backgrounds to prevent any white-out effects on text or arrows.

```mermaid
sequenceDiagram
    autonumber
    %% Participants with visible borders
    participant U as User
    participant F as Frontend (Client)
    participant B as Backend (Flask)
    participant AI as Gemini 2.5 Flash
    participant TTS as TTS Engine

    Note over U, F: PHASE 1: INPUT CAPTURE
    U->>F: Performs facial expression / Types text
    F->>B: Sends Text message + Base64 Frame (every 500ms)

    Note over B, AI: PHASE 2: PROCESSING & INTELLIGENCE
    
    B->>B: OpenCV ROI Face Cropping
    B->>B: Emotion Classification (HuggingFace)
    B->>B: Weighted Mood Calculation (60s Window)
    
    B->>AI: Internal Tag [USER STATE: Mood] + User Text
    AI-->>B: Empathetic Natural Language Response

    Note over B, U: PHASE 3: FEEDBACK LOOP
    B->>TTS: Generate Audio from AI Text (pyttsx3)
    B->>F: Emit 'ai_response' (Audio URL + Mood Key)
    F->>F: Trigger Three.js Lip-Sync & Animation
    F->>U: Kai responds with voice and text

```

---

## 📊 Technical Stack Breakdown

| Category | Technology Used |
| --- | --- |
| **Backend** | Python, Flask, Flask-SocketIO |
| **Frontend** | HTML5, CSS3, JavaScript (ES6), Three.js |
| **AI (Language)** | Google Generative AI (Gemini 2.5 Flash) |
| **Computer Vision** | OpenCV, HuggingFace Transformers |
| **Speech** | pyttsx3 (Text-to-Speech) |
| **Avatar Rendering** | TalkingHead library |

---

## ⚙️ Installation & Setup

1. **Clone the Repository:**
```bash
git clone https://github.com/rutujakumbhar17/kai-the-companion.git
cd Kai-The-Companion

```


2. **Install Dependencies:**
```bash
pip install -r requirements.txt

```


3. **Configure API Key:**
Create a `config.py` file in the root directory:
```python
apikey = "YOUR_GEMINI_API_KEY"

```


4. **Run the Server:**
```bash
python app.py

```



Access the application at `http://127.0.0.1:5000`.
