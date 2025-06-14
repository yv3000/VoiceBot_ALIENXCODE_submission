import os
import json
import speech_recognition as sr
from pydub import AudioSegment
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from transformers import pipeline
from langdetect import detect

# --- Initialization ---
app = Flask(__name__)
load_dotenv()

# --- Configure Gemini API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("🔴 GOOGLE_API_KEY not found. Please set it in the .env file.")
genai.configure(api_key=GOOGLE_API_KEY)

# --- Load Knowledge Base ---
try:
    with open('kb.json', 'r', encoding='utf-8') as f:
        KNOWLEDGE_BASE = json.load(f)
        KB_CONTEXT_STRING = json.dumps(KNOWLEDGE_BASE)
    print("✅ Knowledge base loaded.")
except FileNotFoundError:
    print("⚠️ Warning: kb.json not found.")
    KNOWLEDGE_BASE = []
    KB_CONTEXT_STRING = ""

# --- Load AI Models ---
MODELS = {}
try:
    print("🤖 Loading translation models...")
    # Add all your language models here
    MODELS['en_to_hi_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-en-hi")
    MODELS['en_to_mr_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-en-mr")
    MODELS['hi_to_en_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-hi-en")
    MODELS['mr_to_en_translator'] = pipeline("translation", model="Helsinki-NLP/opus-mt-mr-en")
    print("✅ All translation models loaded.")
except Exception as e:
    print(f"🔴 Could not load translation models: {e}. Multi-language support may be limited.")

# --- Dialogue Management System ---
conversation_history = []
MAX_HISTORY_LENGTH = 8

def translate_text(text, model_key):
    # ... (This function remains unchanged)
    if model_key not in MODELS:
        print(f"⚠️ Translator model '{model_key}' not found.")
        return text
    try:
        return MODELS[model_key](text)[0]['translation_text']
    except Exception as e:
        print(f"Error during translation with {model_key}: {e}")
        return text

def get_ai_response(query, history, source_lang='en'):
    # ... (This function remains unchanged)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['text']}" for msg in history])
    language_instruction = ""
    if source_lang == 'hi':
        language_instruction = "IMPORTANT: Your final response MUST be in Hinglish (Hindi written in English letters)."
    elif source_lang == 'mr':
        language_instruction = "IMPORTANT: Your final response MUST be translated into Marathi (using Devanagari script)."
    prompt = f"""You are ALIENX...""" # Keeping this prompt the same
    try:
        response = model.generate_content(prompt)
        final_response_text = response.text.strip()
        if source_lang == 'mr':
            final_response_text = translate_text(final_response_text, 'en_to_mr_translator')
        return final_response_text
    except Exception as e:
        print(f"🔴 Error calling Gemini API: {e}")
        return "I am experiencing a communication error with my core matrix. Please try again."

def process_and_get_response(transcript):
    """A centralized function to handle transcription logic to avoid repetition."""
    global conversation_history
    if not transcript:
        return jsonify({'response': 'No intelligible data received.'}), 400

    try:
        detected_lang = detect(transcript)
        print(f"[Detection] Detected language: {detected_lang}")
    except Exception as e:
        print(f"Language detection failed: {e}. Defaulting to English.")
        detected_lang = 'en'

    processing_transcript = transcript
    if detected_lang == 'hi':
        processing_transcript = translate_text(transcript, 'hi_to_en_translator')
    elif detected_lang == 'mr':
        processing_transcript = translate_text(transcript, 'mr_to_en_translator')

    response_text = get_ai_response(processing_transcript, conversation_history, source_lang=detected_lang)
    print(f"[AI Response] (Source Lang: {detected_lang}): '{response_text}'")

    conversation_history.append({'role': 'user', 'text': processing_transcript})
    conversation_history.append({'role': 'assistant', 'text': response_text})
    if len(conversation_history) > MAX_HISTORY_LENGTH:
        conversation_history = conversation_history[-MAX_HISTORY_LENGTH:]

    tts_lang_code = {'en': 'en-US', 'hi': 'hi-IN', 'mr': 'mr-IN'}.get(detected_lang, 'en-US')
    return jsonify({'response': response_text, 'lang': tts_lang_code})

# --- API Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_text_query():
    """Processes queries from voice or text input."""
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    return process_and_get_response(transcript)

# --- NEW: Audio Upload Endpoint ---
@app.route('/upload_audio', methods=['POST'])
def process_audio_query():
    """Processes queries from an uploaded .wav file."""
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        recognizer = sr.Recognizer()
        try:
            # pydub helps ensure the file is in a readable format
            audio = AudioSegment.from_wav(file)
            audio.export("temp.wav", format="wav") # Re-export to a clean WAV
            
            with sr.AudioFile("temp.wav") as source:
                audio_data = recognizer.record(source)
                print("[Audio] Transcribing uploaded audio file...")
                # Using Google's free web-based STT for file transcription
                transcript = recognizer.recognize_google(audio_data)
                print(f"[Audio] Transcription: '{transcript}'")
                
                # Now that we have the text, we use the same processing logic
                return process_and_get_response(transcript)
                
        except sr.UnknownValueError:
            print("[Audio Error] Google Speech Recognition could not understand audio")
            return jsonify({'response': "I'm sorry, I could not understand the audio in the file.", 'lang': 'en-US'}), 400
        except sr.RequestError as e:
            print(f"[Audio Error] Could not request results from Google Speech Recognition service; {e}")
            return jsonify({'response': "Could not connect to the speech recognition service.", 'lang': 'en-US'}), 500
        except Exception as e:
            print(f"[Audio Error] An error occurred: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear_history():
    global conversation_history
    conversation_history = []
    print("\n[History] Conversation history cleared.")
    return jsonify({'status': 'cleared'})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)