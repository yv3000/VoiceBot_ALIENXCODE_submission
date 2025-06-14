import os
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from transformers import pipeline

# --- Initialization ---
app = Flask(__name__)
load_dotenv()  # Load environment variables from .env file

# --- Configure Gemini API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found. Please set it in the .env file.")
genai.configure(api_key=GOOGLE_API_KEY)

# --- Load Knowledge Base from JSON file ---
try:
    with open('kb.json', 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = json.load(f)
        KB_CONTEXT_STRING = json.dumps(KNOWLEDGE_BASE) # Convert KB to a string for the prompt
    print("✅ Knowledge base loaded and prepared for AI context.")
except FileNotFoundError:
    print("⚠️ Warning: kb.json not found. The assistant will rely solely on Gemini.")
    KNOWLEDGE_BASE = []
    KB_CONTEXT_STRING = ""

# --- Load Translation Models (Kept for multi-language support) ---
MODELS = {}
try:
    print("🤖 Loading translation models...")
    MODELS['en_to_hi_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-en-hi")
    MODELS['hi_to_en_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-hi-en")
    print("✅ Translation models loaded.")
except Exception as e:
    print(f"🔴 Could not load translation models: {e}. Multi-language support will be disabled.")

def translate_text(text, model_key):
    """Translates text using a specified model."""
    if model_key not in MODELS:
        return text # Return original text if translator failed to load
    try:
        result = MODELS[model_key](text)
        return result[0]['translation_text']
    except Exception as e:
        print(f"Error during translation: {e}")
        return text

# --- NEW: Function to generate response with Gemini ---
def get_ai_response(query):
    """
    Generates a response using the Gemini API, prioritizing the Knowledge Base.
    This is a form of Retrieval-Augmented Generation (RAG).
    """
    # Using the latest fast and efficient model
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    # This special prompt instructs Gemini to use your KB first and adopts the new persona
    prompt = f"""
    You are an advanced AI assistant named ALIENX, created by ALIENXCODE.
    Your primary function is to answer user questions based on the provided internal knowledge base about LenDenClub.

    INTERNAL KNOWLEDGE BASE:
    ---
    {KB_CONTEXT_STRING}
    ---

    USER'S QUESTION: "{query}"

    INSTRUCTIONS:
    1.  First, analyze the USER'S QUESTION to understand its intent.
    2.  If the question is about LenDenClub, search the INTERNAL KNOWLEDGE BASE for a very close match. If found, provide the answer *exactly* as written.
    3.  If the user's question is a simple greeting, respond with a cool, futuristic greeting befitting the name ALIENX.
    4.  If, and only if, the question is not in the knowledge base, use your general intelligence to provide a concise and helpful response.
    5.  Your response must only be the final answer. Do not add introductory phrases like "Based on the knowledge base...".
    """

    print("--- Transmitting prompt to Gemini a.k.a ALIENX ---")

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"🔴 Error communicating with Gemini Core: {e}")
        if "response.prompt_feedback" in locals() and response.prompt_feedback.block_reason:
            return "Transmission blocked by a safety protocol. Please rephrase."
        return "I seem to be experiencing a communication error with my core matrix. Please try again."
# --- API Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_query():
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    lang = data.get('lang', 'en-US')
    
    print(f"\n[Request] Language: {lang}, Transcript: '{transcript}'")
    
    if not transcript:
        return jsonify({'response': 'Sorry, I did not hear anything.'}), 400

    # 1. Translate query to English if necessary
    processing_transcript = transcript
    if lang == 'hi-IN' and 'hi_to_en_translator' in MODELS:
        processing_transcript = translate_text(transcript, 'hi_to_en_translator')
        print(f"[Translation] hi->en: '{processing_transcript}'")

    # 2. Get the response from our new Gemini function (handles KB and fallback)
    response_text = get_ai_response(processing_transcript)
    print(f"[AI Response] (in English): '{response_text}'")

    # 3. Translate response back to the original language if necessary
    final_response = response_text
    if lang == 'hi-IN' and 'en_to_hi_translator' in MODELS:
        final_response = translate_text(response_text, 'en_to_hi_translator')
        print(f"[Translation] en->hi: '{final_response}'")

    return jsonify({'response': final_response, 'lang': lang})

# We keep use_reloader=False to prevent models loading twice in debug mode
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)