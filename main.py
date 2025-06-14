import os
import json
import re
import tempfile
import warnings
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from transformers import pipeline, logging as hf_logging
import speech_recognition as sr
from pydub import AudioSegment
import torch

# --- Suppress Warnings for Cleaner Output ---
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

# --- Secure Model Loading ---
original_torch_load = torch.load
def safe_torch_load(*args, **kwargs):
    kwargs['weights_only'] = True
    return original_torch_load(*args, **kwargs)
torch.load = safe_torch_load

# --- Backend Initialization ---
app = Flask(__name__)
load_dotenv()
hf_logging.set_verbosity_error()

# --- Google Gemini API Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("🔴 CRITICAL: GOOGLE_API_KEY not found in .env file. The application cannot start.")
genai.configure(api_key=GOOGLE_API_KEY)

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]
MODEL_CONFIG = {"temperature": 0.75, "top_p": 0.95, "top_k": 40}

# --- Knowledge Base & NLP Model Loading ---
try:
    # Use an absolute path to ensure the file is found regardless of where the script is run
    KB_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb.json')
    with open(KB_FILE_PATH, 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = json.load(f)
    print(f"✅ Knowledge Base loaded successfully from {KB_FILE_PATH} with {len(KNOWLEDGE_BASE)} articles.")
except Exception as e:
    KNOWLEDGE_BASE = []
    print(f"🔴 WARNING: Could not load kb.json: {e}. RAG/specialist-knowledge will be disabled.")

# Load models (no changes needed here)
MODELS = {}
try:
    print("🤖 Loading multilingual translation models...")
    MODELS['hi_to_en'] = pipeline("translation", model="Helsinki-NLP/opus-mt-hi-en")
    MODELS['mr_to_en'] = pipeline("translation", model="Helsinki-NLP/opus-mt-mr-en")
    print("✅ Multilingual models loaded successfully.")
except Exception as e:
    print(f"🔴 WARNING: Could not load translation models: {e}. Non-English support will be limited.")

# --- Dialogue Management (In-Memory) ---
session_history = []
MAX_SESSION_HISTORY = 8

# A more comprehensive list of stopwords for better keyword extraction
STOPWORDS = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'tell', 'me', 'about', 'explain', 'give', 'information'])

# --- Core Logic Components ---

def retrieve_knowledge(query):
    """Finds the most relevant article from the KB using keyword matching."""
    if not KNOWLEDGE_BASE:
        return []
    query_keywords = set(re.findall(r'\b\w+\b', query.lower())) - STOPWORDS
    if not query_keywords:
        return []
    
    scored_articles = []
    for article in KNOWLEDGE_BASE:
        # Give higher weight to keywords in the 'question' field
        question_keywords = set(re.findall(r'\b\w+\b', article['question'].lower()))
        answer_keywords = set(re.findall(r'\b\w+\b', article['answer'].lower()))
        
        # Simple scoring: 2 points for a question keyword match, 1 for an answer keyword match
        score = len(query_keywords.intersection(question_keywords)) * 2 + len(query_keywords.intersection(answer_keywords))

        if score > 2:  # Increased threshold for better relevance
            scored_articles.append((score, article))
    
    if not scored_articles:
        return []

    scored_articles.sort(key=lambda x: x[0], reverse=True)
    return [article for _, article in scored_articles[:1]] # Return only the top match

def generate_ai_core_response(query, source_lang='en-IN'):
    """
    Generates a response using a hybrid approach:
    1.  Uses the KB as a primary source if relevant.
    2.  Falls back to general knowledge if the KB is not relevant.
    """
    global session_history
    retrieved_data = retrieve_knowledge(query)
    formatted_history = "\n".join([f"{msg['role']}: {msg['text']}" for msg in session_history])
    lang_map = {'en-IN': 'English', 'hi-IN': 'Hindi or Hinglish', 'mr-IN': 'Marathi'}
    output_language = lang_map.get(source_lang, 'English')

    # ⭐ UPDATED PROMPT FOR A MORE HUMAN-LIKE PERSONALITY ⭐
    prompt = f"""
    **System Persona:** You are ALIENX. Your persona is that of a calm, intelligent, and highly capable human assistant.
    - **Your Tone:** Be conversational, clear, and natural. Avoid being overly robotic or formal. Use phrases like "Sure, I can help with that," or "It looks like..." to start your sentences. Be friendly, yet professional. Use contractions like "it's" or "you're" to sound more human.

    **Guiding Principles (MUST FOLLOW):**
    1.  **Knowledge Base Priority:** The `Retrieved Knowledge` section is your single source of truth for specific topics.
        - **If `Retrieved Knowledge` is NOT empty:** Base your answer on it. Your main task is to synthesize this information into a natural, conversational response.
        - **If `Retrieved Knowledge` is empty:** Answer the query using your vast general knowledge.
    2.  **Language Adherence:** Your final `response_text` must be in the `Required Output Language`.

    **Context for Analysis:**
    - **User Query:** "{query}"
    - **Retrieved Knowledge (Source of Truth):** {json.dumps(retrieved_data, indent=2)}
    - **Conversation History:** "{formatted_history}"
    - **Required Output Language:** {output_language}

    **Your Response (MUST be a single, valid JSON object):**
    {{
      "thought_process": "string | Explain your reasoning. Did you use the knowledge base or general knowledge? Why?",
      "response_text": "string | The final, natural language response for the user, following all principles.",
      "confidence_score": "number | From 0.0 to 1.0 based on your confidence."
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest', generation_config=MODEL_CONFIG, safety_settings=SAFETY_SETTINGS)
        raw_response = model.generate_content(prompt).text
        
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not match:
            print(f"🔴 AI Core Warning: LLM did not return a JSON object. Raw output: {raw_response}")
            return {"response_text": raw_response or "I am having trouble formatting my thoughts. Please try again.", "confidence_score": 0.2}

        ai_response_obj = json.loads(match.group(0))

        session_history.append({'role': 'user', 'text': query})
        session_history.append({'role': 'assistant', 'text': ai_response_obj.get('response_text', '')})
        session_history = session_history[-MAX_SESSION_HISTORY:]
        
        return ai_response_obj

    except Exception as e:
        print(f"🔴 AI Core Error: {e}\nRaw Gemini Output was:\n{raw_response if 'raw_response' in locals() else 'Not available'}")
        return {
            "response_text": "I'm experiencing a temporary issue with my core logic. Please ask your question again in a moment.",
            "confidence_score": 0.0
        }

def translate_query_to_english(text, lang_code):
    """Translates text to English if a model is available."""
    translator_key = f"{lang_code.split('-')[0]}_to_en"
    if lang_code.startswith('en') or translator_key not in MODELS:
        return text
    try:
        return MODELS[translator_key](text)[0]['translation_text']
    except Exception as e:
        print(f"🔴 Translation Error for lang {lang_code}: {e}")
        return text

# --- API Endpoints (No changes needed below this line) ---
@app.route('/process_query', methods=['POST'])
def process_query_endpoint():
    try:
        data = request.json
        transcript = data.get('transcript', '').strip()
        lang = data.get('language', 'en-IN')

        if not transcript:
            return jsonify({'response': 'No input received. Please say something.', 'lang': 'en-US'}), 400

        english_query = translate_query_to_english(transcript, lang)
        ai_response = generate_ai_core_response(english_query, source_lang=lang)
        
        return jsonify({'response': ai_response.get('response_text', "I'm sorry, I couldn't generate a response."), 'lang': lang})

    except Exception as e:
        print(f"🔴 Unhandled error in /process_query: {e}")
        return jsonify({'response': 'A critical server error occurred. Please try again later.', 'lang': 'en-US'}), 500

@app.route('/upload_audio', methods=['POST'])
def upload_audio_endpoint():
    try:
        if 'audio_file' not in request.files:
            return jsonify({'response': 'No audio file found in the request.', 'lang': 'en-US'}), 400
            
        file = request.files['audio_file']
        recognizer = sr.Recognizer()

        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_wav:
            AudioSegment.from_file(file).export(temp_wav.name, format="wav")
            with sr.AudioFile(temp_wav.name) as source:
                audio_data = recognizer.record(source)
        
        transcript = recognizer.recognize_google(audio_data, language="en-IN")
        
        ai_response = generate_ai_core_response(transcript, source_lang='en-IN')
        return jsonify({'response': ai_response.get('response_text'), 'lang': 'en-IN'})

    except sr.UnknownValueError:
        return jsonify({'response': 'Audio was unclear. I could not understand the contents.', 'lang': 'en-US'}), 200
    except Exception as e:
        print(f"🔴 Unhandled error in /upload_audio: {e}")
        return jsonify({'response': 'An error occurred while processing the audio file.', 'lang': 'en-US'}), 500

@app.route('/clear_context', methods=['POST'])
def clear_context_endpoint():
    global session_history
    session_history = []
    print("Dialogue context has been reset by the user.")
    return jsonify({'status': 'Context cleared.'}), 200

@app.route('/')
def index_route():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, port=5000)