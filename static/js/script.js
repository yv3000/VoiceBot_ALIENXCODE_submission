/**
 * ALIENX - Conversational Intelligence Assistant (Version 4.5 - Professional Refined)
 * UI: Grok-inspired, Monochrome, Fully Responsive.
 * Voice: Employs the highest-quality, most natural system voices available in the browser.
 */
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const voiceBtn = document.getElementById('voiceBtn');
    const statusDiv = document.getElementById('status');
    const chatContainer = document.getElementById('chatContainer');
    const clearBtn = document.getElementById('clearBtn');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const audioUploadInput = document.getElementById('audioUploadInput');
    const languageSelector = document.getElementById('languageSelector');

    let isRecording = false;
    let ttsVoices = [];
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    // --- Core Functions ---
    function setupSpeechRecognition() {
        if (!SpeechRecognition) {
            updateStatus('Error: Voice recognition not supported.');
            addMessage('system-error', 'Your browser does not support the Web Speech API. Voice input is disabled.');
            voiceBtn.disabled = true;
            return;
        }
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = languageSelector.value;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            voiceBtn.classList.add('recording');
            updateStatus('Listening...');
            updatePipelineStep('input', 'active', 'VOICE INPUT');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            updatePipelineStep('input', 'completed', 'TRANSCRIBED');
            handleUserInput(transcript, languageSelector.value);
        };

        recognition.onend = () => {
            isRecording = false;
            voiceBtn.classList.remove('recording');
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            const errorMessage = `Mic Error: ${event.error}. Please check permissions.`;
            addMessage('system-error', errorMessage);
            resetPipeline();
        };
    }

    async function handleUserInput(text, lang) {
        if (!text) return;
        speechSynthesis.cancel();
        addMessage('user', text);
        showTypingIndicator();
        await sendToServer('/process_query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript: text, language: lang }),
        });
    }

    async function sendToServer(endpoint, options) {
        updateStatus('Thinking...');
        updatePipelineStep('detect', 'active', 'ANALYZING...');

        try {
            const response = await fetch(endpoint, options);
            updatePipelineStep('detect', 'completed', 'ANALYZED');
            updatePipelineStep('core', 'active', 'THINKING...');
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.response || `HTTP error! Status: ${response.status}`);
            }
            handleServerResponse(data);
        } catch (error) {
            console.error('Server communication error:', error);
            removeTypingIndicator();
            addMessage('system-error', `System Alert: ${error.message}`);
            updateStatus('Anomaly Detected.');
            resetPipeline();
        }
    }
    
    function handleServerResponse(data) {
        removeTypingIndicator();
        updatePipelineStep('core', 'completed', 'RESPONSE READY');
        updatePipelineStep('response', 'active', 'GENERATING AUDIO');
        
        addMessage('assistant', data.response);
        speakResponse(data.response, data.lang);
        
        setTimeout(() => {
            updatePipelineStep('response', 'completed', 'TRANSMITTED');
            updateStatus('System online. Awaiting directive.');
            resetPipeline();
        }, 1000);
    }

    /**
     * Finds and uses the highest-quality, most natural-sounding voice available in the browser.
     * This version is simplified and more robust.
     */
    function speakResponse(text, lang = 'en-US') {
        if (!text || !('speechSynthesis' in window)) {
            console.warn('SpeechSynthesis not supported or text is empty.');
            return;
        }

        // Create a function to speak with the best available voice
        const playSpeech = () => {
            speechSynthesis.cancel(); // Cancel any ongoing speech
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang;

            const voices = speechSynthesis.getVoices();
            const voicesForLang = voices.filter(v => v.lang.toLowerCase().startsWith(lang.split('-')[0].toLowerCase()));

            let bestVoice = null;
            
            // Priority 1: Find high-quality voices by name keywords. 'Neural' is key for MS Edge.
            const highQualityNames = /google|microsoft|apple|natural|neural|zira|david|rishi|lekha/i;
            bestVoice = voicesForLang.find(v => highQualityNames.test(v.name));

            // Priority 2: If none found, find any non-local (cloud-based) voice.
            if (!bestVoice) {
                bestVoice = voicesForLang.find(v => !v.localService);
            }

            // Priority 3: As a last resort, take the first available voice for the language.
            if (!bestVoice && voicesForLang.length > 0) {
                bestVoice = voicesForLang[0];
            }

            if (bestVoice) {
                utterance.voice = bestVoice;
                console.log(`%cUsing Voice: ${bestVoice.name} (${bestVoice.lang})`, 'color: lightgreen; font-weight: bold;');
            } else {
                console.warn(`No suitable voice found for language ${lang}. Using browser default.`);
            }
            
            utterance.onerror = (event) => {
                console.error('SpeechSynthesis Error:', event.error);
                addMessage('system-error', `A voice output error occurred: ${event.error}`);
            };

            speechSynthesis.speak(utterance);
        };

        // The 'voiceschanged' event is crucial. Voices may load asynchronously.
        if (speechSynthesis.getVoices().length === 0) {
            speechSynthesis.addEventListener('voiceschanged', playSpeech, { once: true });
        } else {
            playSpeech();
        }
    }
    
    // --- UI & Helper Functions ---
    const addMessage = (sender, text) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };
    
    const showTypingIndicator = () => {
        if (document.querySelector('.message.typing')) return;
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message typing';
        typingDiv.innerHTML = '<span>●</span><span>●</span><span>●</span>';
        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    const removeTypingIndicator = () => {
        const typingIndicator = document.querySelector('.message.typing');
        if (typingIndicator) typingIndicator.remove();
    }

    const updateStatus = (message) => { statusDiv.textContent = message; };

    const updatePipelineStep = (stepId, statusClass, message) => {
        const step = document.getElementById(`step-${stepId}`);
        if (step) {
            step.className = `pipeline-step ${statusClass}`;
            step.querySelector('.step-status').textContent = message;
        }
    };
    
    const resetPipeline = () => {
        setTimeout(() => {
            ['input', 'detect', 'core', 'response'].forEach(id => {
                updatePipelineStep(id, '', id === 'input' ? 'STANDBY' : 'AWAITING');
            });
        }, 2000);
    };

    async function clearChat() {
        speechSynthesis.cancel();
        chatContainer.innerHTML = '';
        addMessage('assistant', 'Context cleared. How may I assist you now?');
        resetPipeline();
        updateStatus('System online. Awaiting directive.');
        await fetch('/clear_context', { method: 'POST' });
    }

    // --- Event Listeners & Initialization ---
    function initialize() {
        setupSpeechRecognition();

        // Ensure voices are loaded. The main logic is now inside speakResponse.
        speechSynthesis.getVoices(); 
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = () => console.log('System voices reloaded.');
        }

        voiceBtn.addEventListener('click', () => isRecording ? recognition.stop() : recognition.start());

        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const userText = chatInput.value.trim();
            if (!userText) return;
            chatInput.value = '';
            handleUserInput(userText, languageSelector.value);
        });
        
        audioUploadInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                updatePipelineStep('input', 'active', 'FILE UPLOAD');
                const formData = new FormData();
                formData.append('audio_file', file);
                showTypingIndicator();
                sendToServer('/upload_audio', { method: 'POST', body: formData });
            }
            e.target.value = null;
        });

        clearBtn.addEventListener('click', clearChat);

        languageSelector.addEventListener('change', (e) => {
            if (recognition) { recognition.lang = e.target.value; }
        });
    }

    initialize();
});