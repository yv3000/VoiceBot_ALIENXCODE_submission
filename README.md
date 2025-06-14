# ALIENX Voicebot - Team ALIENXCODE Submission

## 1. Project Overview

**ALIENX** is a state-of-the-art P2P Lending Awareness & Sales voicebot, engineered to replicate the fluency, adaptability, and empathy of a human sales representative. Our solution is designed to educate potential users about Peer-to-Peer lending and guide them through the initial sales process.

Our architecture leverages a sophisticated Retrieval-Augmented Generation (RAG) model powered by Google's Gemini API, grounded by a curated knowledge base from `data/kb.json`. The system features a modular design, a professional "Grok-inspired" user interface, and multi-language capabilities.

### Key Features ("Gaining the Edge")

*   **Strategic Prompt Architecture:** Our core `response_gen` module uses advanced prompt engineering to give ALIENX a calm, intelligent, and human-like persona.
*   **Elegant Error & Ambiguity Resolution:** The system is designed to ask intelligent clarifying questions when faced with vague queries, ensuring a smooth conversational flow and avoiding dead ends.
*   **Seamless Multilingual Dexterity:** The NLP pipeline can detect Hindi/Marathi input, translate it for processing, and generate a response in the user's original language, controlled via a UI selector.
*   **Hyper-Realistic Voice Synthesis:** The frontend (`script.js`) intelligently selects the highest-quality, most natural-sounding system voice available in the browser (prioritizing cloud-based voices like Google, Microsoft, and Apple).
*   **Proactive Conversational Guidance:** The AI is instructed to not just answer questions but to proactively guide the conversation, suggesting next steps like a real sales associate.

---

## 2. Environment Setup Instructions

**IMPORTANT:** Using a clean virtual environment is **mandatory** to avoid package conflicts.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/voicebot_ALIENXCODE_submission.git
    cd voicebot_ALIENXCODE_submission
    ```

2.  **Create and Activate a Virtual Environment:**
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *You should see `(venv)` at the beginning of your terminal prompt.*

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: For audio processing, you may need to install `ffmpeg`. You can download it from the official site and add it to your system's PATH.*

4.  **Create the `.env` file** in the root directory and add your secret API key:
    ```
    GOOGLE_API_KEY="YOUR_GEMINI_API_KEY_HERE"
    ```

---

## 3. How to Run for Hackathon Evaluation

### Round 1: Batch Inference

The `run_inference.py` script is used for programmatic evaluation. It reads a CSV, generates responses, and saves a new CSV. **Ensure your virtual environment is activated.**

**Command to Run:**
```bash
python run_inference.py --input path/to/test.csv --output path/to/submission.csv