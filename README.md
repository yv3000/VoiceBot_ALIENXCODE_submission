# ALIENX Voice AI 

### A Smart Voice Assistant by `<ALIENXCODE/>`

**ALIENX Voice AI** is a sleek, minimal, and futuristic voice assistant powered by the Google Gemini API. It supports real-time conversation, voice interaction, multi-language processing, and a custom knowledge base.



## 🔥 Features

* **Smart Conversations** – Uses Gemini (`gemini-1.5-flash-latest`) for fast and context-aware responses.
* **Custom Knowledge Base** – Answers domain-specific queries from a local `kb.json` file using RAG.
* **Voice Input** – Converts speech to text using the Web Speech API.
* **Voice Output** – Speaks responses aloud using text-to-speech.
* **Multi-Language Support** – Understands and translates between English and Hindi.
* **Clean UI** – Minimalist black-and-white theme with cyan accents.
* **Live Status** – Shows real-time processing steps (voice ➜ text ➜ AI ➜ speech).


## 🛠 Tech Stack

| Area        | Technologies Used                    |
| ----------- | ------------------------------------ |
| Backend     | Python, Flask                        |
| AI/NLP      | Google Gemini API, Transformers      |
| Frontend    | HTML, CSS, JavaScript                |
| Speech APIs | Web Speech API (for STT & TTS)       |
| Environment | `python-dotenv` for managing secrets |



### 📂 Project Structure

voice-ai-assistant/
├── .env # Store your Google API Key
├── .gitignore # Ignore sensitive files and virtual env
├── app.py # Flask backend
├── kb.json # Custom knowledge base
├── requirements.txt # Python dependencies
├── README.md # Project documentation
├── templates/
│ └── index.html # Main web page
└── static/
├── css/
│ └── style.css # Styling
└── js/
└── script.js # Frontend logic


## 🚀 Getting Started

### Prerequisites

* Python 3.8 or higher
* A Google Gemini API Key (Get it from [Google AI Studio](https://aistudio.google.com/app/apikey))

### 1. Clone the Repository

bash
git clone https://github.com/your-username/voice-ai-assistant.git
cd voice-ai-assistant


### 2. Set the API Key

Create a `.env` file in the project root:

env
GOOGLE_API_KEY="your-google-api-key-here"


> Do **not** share your `.env` file or upload it to GitHub.

### 3. Create a Virtual Environment

**On macOS/Linux:**


python3 -m venv venv
source venv/bin/activate


**On Windows:**


python -m venv venv
.\venv\Scripts\activate


### 4. Install Dependencies


pip install -r requirements.txt


### 5. Run the Application


flask run


Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.



## How to Use

1. Open the app in a browser (Chrome/Edge recommended).
2. Allow microphone access when prompted.
3. Choose your language (English or Hindi).
4. Click the cyan mic button and start talking!

