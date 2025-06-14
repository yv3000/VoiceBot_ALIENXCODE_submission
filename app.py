# ==============================================================================
# ALIENX - Conversational Intelligence Assistant
# Team: ALIENXCODE
# Backend Service: Implements the full technical architecture
# ==============================================================================

import os
import json
import re
import tempfile
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from transformers import pipeline, logging as hf_logging
from langdetect import detect
import speech_recognition as sr
from pydub import AudioSegment

# --- Component 7: Backend Services & Infrastructure (Initialization) ---
# Using Flask as the web framework and python-dotenv for config management.
# This entire file acts as the backend service layer.
# --------------------------------------------------------------------------
app = Flask(__name__)
load_dotenv()
hf_logging.set_verbosity_error()

# Configure Google Gemini API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found in .env file. Please add it.")
genai.configure(api_key=GOOGLE_API_KEY)

# Load Knowledge Base
try:
    with open('kb.json', 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = json.load(f)
    print(f"✅ Knowledge Base loaded with {len(KNOWLEDGE_BASE)} articles.")
except Exception as e:
    KNOWLEDGE_BASE = []
    print(f"🔴 Critical Error loading kb.json: {e}")

# Load Multilingual Models (Part of the advanced NLP pipeline)
MODELS = {}
try:
    print("🤖 Loading multilingual models for NLP pipeline...")
    # These models are used for normalizing non-English input into English for the core AI
    MODELS['hi_to_en'] = pipeline("translation", model="Helsinki-NLP/opus-mt-hi-en")
    MODELS['mr_to_en'] = pipeline("translation", model="Helsinki-NLP/opus-mt-mr-en")
    print("✅ Multilingual models loaded.")
except Exception as e:
    print(f"🔴 Could not load translation models: {e}. Non-English support will be disabled.")


# --- Component 4: Dialogue Management System (Context Memory) ---
# Maintains conversation context across multiple turns.
# ------------------------------------------------------------------
session_history = []
MAX_SESSION_HISTORY = 8 # Keeps the context window for the LLM manageable

# --- Component 3: NLP Pipeline (Helper Functions) ---
# Functions for text preprocessing and normalization.
# -------------------------------------------------------
def translate_to_english(text, source_lang):
    model_key = f"{source_lang}_to_en"
    if model_key in MODELS:
        try:
            return MODELS[model_key](text)[0]['translation_text']
        except Exception:
            return text
    return text

STOP_WORDS = set(['what', 'who', 'when', 'is', 'are', 'a', 'the', 'tell', 'me', 'about', 'can', 'you'])
def preprocess_text_for_retrieval(text):
    """
    Simplified preprocessing for keyword extraction to find relevant knowledge.
    In a full-scale system, this would be vector embeddings.
    """
    words = re.findall(r'\b\w+\b', text.lower())
    return {word for word in words if word not in STOP_WORDS and not word.isdigit()}


# --- Component 5: Knowledge Retrieval System ---
# Accesses the structured knowledge base (kb.json) to find relevant information.
# This implementation uses a robust keyword search as a prototype for vector search.
# ---------------------------------------------------------------------------------
def retrieve_knowledge(query):
    query_keywords = preprocess_text_for_retrieval(query)
    if not query_keywords: return []

    scored_articles = []
    for article in KNOWLEDGE_BASE:
        question_keywords = preprocess_text_for_retrieval(article['question'])
        common_keywords = query_keywords.intersection(question_keywords)
        
        if common_keywords:
            score = len(common_keywords)
            scored_articles.append((score, article))

    if not scored_articles: return []

    scored_articles.sort(key=lambda x: x[0], reverse=True)
    # Return the single most relevant article to keep the prompt focused
    return [scored_articles[0][1]]


# --- Component 6: Response Generation Module ---
# Constructs the final text response for the user using a Generative LLM.
# This function is the cognitive core, combining NLP, Dialogue Management, and Generation.
# -------------------------------------------------------------------------------
def generate_response(query, source_lang='en'):
    global session_history
    
    # 1. KNOWLEDGE RETRIEVAL
    retrieved_data = retrieve_knowledge(query)
    retrieved_json = json.dumps(retrieved_data, indent=2) if retrieved_data else "[]"

    # 2. CONTEXT PREPARATION (from Dialogue Management)
    formatted_history = "\n".join([f"{msg['role']}: {msg['text']}" for msg in session_history])

    # 3. CONSTRUCTING THE MASTER PROMPT FOR THE GENERATIVE MODEL
    language_instruction = "Your final response MUST be in clear, professional English."
    if source_lang == 'hi': language_instruction = "Your final response MUST be in conversational Hindi (Hinglish)."
    elif source_lang == 'mr': language_instruction = "Your final response MUST be in Marathi."
    
    # This prompt encapsulates the logic for NLP, Dialogue Management, and Response Generation.
    prompt = f"""
    You are ALIENX, an advanced conversational AI. You are acting as the cognitive core for a system. Follow these steps meticulously:

    **1. NLP Pipeline - Analysis:**
    - **User's Query:** "{query}"
    - **Conversation History:** {formatted_history}
    - **Your Knowledge:** You have retrieved the following facts from your knowledge base:
      ```json
      {retrieved_json}
      ```
    - **Your Task:** First, understand the user's intent. Is it a follow-up? Is it ambiguous? Is it a new question?

    **2. Dialogue Management - Decision:**
    - **IF** the user's query is vague (e.g., "tell me more"), ask a clarifying question based on the history or knowledge.
    - **IF** your retrieved knowledge is empty (`[]`), you MUST inform the user you don't have that specific information and suggest an alternative topic you can discuss. Example: "I don't have details on that, but I can tell you about registration or investment risks. What would you like to know?"
    - **ELSE (if knowledge is available)**, proceed to the next step.

    **3. Response Generation - Synthesis:**
    - Synthesize a helpful, natural, and accurate response based *strictly* on the `Your Knowledge` JSON.
    - DO NOT make up information. Ground every part of your answer in the provided facts.
    - Maintain a professional, empathetic, and human-like tone.
    - Adhere to this final language rule: {language_instruction}
    
    **ALIENX Response:**
    """
    
    # 4. EXECUTING THE GENERATION
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        final_text = response.text.strip()
    except Exception as e:
        print(f"🔴 Gemini Error: {e}")
        final_text = "My apologies, my connection to the core intelligence seems to be unstable. Please try again."

    # 5. UPDATE DIALOGUE HISTORY
    session_history.append({'role': 'user', 'text': query})
    session_history.append({'role': 'assistant', 'text': final_text})
    if len(session_history) > MAX_SESSION_HISTORY:
        session_history = session_history[-MAX_SESSION_HISTORY:]

    return final_text

# --- API Endpoint to connect Frontend with Backend ---
# This function orchestrates the entire process from receiving a request to sending a response.
# ------------------------------------------------------------------------------------------
@app.route('/process_query', methods=['POST'])
def process_query_endpoint():
    # 1. Receive input from the frontend (Implements Voice Input + ASR)
    transcript = request.json.get('transcript', '').strip()
    if not transcript:
        return jsonify({'error': 'No transcript received.'}), 400

    # 2. NLP Pipeline - Language Detection & Normalization
    try:
        detected_lang = detect(transcript)
        if detected_lang not in ['en', 'hi', 'mr']: detected_lang = 'en'
    except Exception:
        detected_lang = 'en'
    
    english_query = translate_to_english(transcript, detected_lang) if detected_lang != 'en' else transcript

    # 3. Pass to Core Cognitive Function
    response_text = generate_response(english_query, source_lang=detected_lang)

    # 4. Prepare and Send Response
    tts_lang_code = {'en': 'en-US', 'hi': 'hi-IN', 'mr': 'mr-IN'}.get(detected_lang, 'en-US')
    return jsonify({'response': response_text, 'lang': tts_lang_code})

@app.route('/upload_audio', methods=['POST'])
def upload_audio_endpoint():
    # --- Component 1 & 2: Voice Input (File) & ASR Engine ---
    if 'audio_file' not in request.files or not request.files['audio_file'].filename:
        return jsonify({'response': 'No audio file detected.', 'lang': 'en-US'}), 400

    file = request.files['audio_file']
    recognizer = sr.Recognizer()
    
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_wav:
            AudioSegment.from_file(file).export(temp_wav.name, format="wav")
            with sr.AudioFile(temp_wav.name) as source:
                audio_data = recognizer.record(source)
        
        transcript = recognizer.recognize_google(audio_data, language="en-IN") # Optimized for Indian accents
        request.json = {'transcript': transcript} # Mock request body to reuse main logic
        return process_query_endpoint()

    except sr.UnknownValueError:
        return jsonify({'response': "Audio was unclear. My sensors could not process the transmission.", 'lang': 'en-US'}), 200
    except Exception as e:
        print(f"🔴 Audio Upload Error: {e}")
        return jsonify({'response': "An error occurred during audio file processing.", 'lang': 'en-US'}), 500


@app.route('/clear_context', methods=['POST'])
def clear_context():
    global session_history
    session_history = []
    print("Dialogue context cleared by user.")
    return jsonify({'status': 'Context cleared successfully.'})

@app.route('/')
def root():
    return render_template('index.html')

if __name__ == '__main__':
    # Component 7: Running the Backend Service
    app.run(debug=True, use_reloader=False, port=5000)