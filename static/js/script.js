document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const voiceBtn = document.getElementById('voiceBtn');
    const statusDiv = document.getElementById('status');
    const chatContainer = document.getElementById('chatContainer');
    const clearBtn = document.getElementById('clearBtn');
    const langSelect = document.getElementById('langSelect');

    let isRecording = false;
    let currentLang = langSelect.value;
    let ttsVoices = [];
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    // --- Core Functions ---
    const setupVoices = () => {
        ttsVoices = speechSynthesis.getVoices();
    };
    
    const setupRecognition = () => {
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = currentLang;

            recognition.onstart = () => {
                isRecording = true;
                voiceBtn.classList.add('recording');
                updateStatus('Awaiting transmission...');
                updatePipelineStep('step-voice', 'active', 'RECEIVING');
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                updatePipelineStep('step-voice', 'completed', 'RECEIVED');
                processTranscript(transcript.trim());
            };

            recognition.onend = () => {
                isRecording = false;
                voiceBtn.classList.remove('recording');
                if (statusDiv.textContent === 'Awaiting transmission...') {
                     updateStatus('Transmission timed out. Awaiting new directive.');
                     resetPipeline();
                }
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                updateStatus(`Error: ${event.error}.`);
                resetPipeline();
            };

        } else {
            updateStatus('Speech recognition not supported.');
            voiceBtn.disabled = true;
            langSelect.disabled = true;
        }
    };
    
    const processTranscript = async (transcript) => {
        if (!transcript) {
            updateStatus('No intelligible data received.');
            resetPipeline();
            return;
        }

        addMessage('user', transcript);
        updateStatus('Analyzing transmission...');
        
        // Update Pipeline UI
        updatePipelineStep('step-asr', 'active', 'DECRYPTING');
        
        try {
            updatePipelineStep('step-asr', 'completed', 'COMPLETE');
            updatePipelineStep('step-nlp', 'active', 'PROCESSING');
            
            // API Call to Flask Backend with language info
            const res = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transcript: transcript, lang: currentLang })
            });

            if (!res.ok) throw new Error(`Server connection error: ${res.status}`);

            const data = await res.json();
            
            // UI update for backend processing complete
            updatePipelineStep('step-nlp', 'completed', 'COMPLETE');
            updatePipelineStep('step-response', 'active', 'GENERATING');

            addMessage('assistant', data.response);
            speakResponse(data.response, data.lang);

            updatePipelineStep('step-response', 'completed', 'COMPLETE');
            updateStatus('System ready. Awaiting directive.');

            setTimeout(resetPipeline, 4000);

        } catch (error) {
            console.error('Error processing request:', error);
            const errorMessage = "Connection to my core matrix has been disrupted. Please verify server protocols and try again.";
            addMessage('assistant', errorMessage);
            updateStatus('Connection Anomaly Detected');
            resetPipeline();
        }
    };
    
    const speakResponse = (text, lang) => {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang;

            const voice = ttsVoices.find(v => v.lang === lang);
            if (voice) {
                utterance.voice = voice;
            }

            speechSynthesis.speak(utterance);
        }
    };
    
    // --- UI & Helper Functions ---
    const addMessage = (sender, text) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };
    
    const updateStatus = (message) => statusDiv.textContent = message;

    const updatePipelineStep = (stepId, status, message) => {
        const step = document.getElementById(stepId);
        if (step) {
            step.className = `pipeline-step ${status}`;
            step.querySelector('.step-status').textContent = message;
        }
    };

    const resetPipeline = () => {
        updatePipelineStep('step-voice', '', 'STANDBY');
        updatePipelineStep('step-asr', '', 'AWAITING');
        updatePipelineStep('step-nlp', '', 'AWAITING');
        updatePipelineStep('step-response', '', 'AWAITING');
    };

    const clearChat = () => {
        chatContainer.innerHTML = '';
        addMessage('assistant', 'Log cleared. Awaiting new directive.');
        resetPipeline();
        updateStatus('System ready.');
    };
    
    // --- Event Listeners ---
    voiceBtn.addEventListener('click', () => {
        if (!recognition) return;
        isRecording ? recognition.stop() : recognition.start();
    });
    
    clearBtn.addEventListener('click', clearChat);

    langSelect.addEventListener('change', () => {
        currentLang = langSelect.value;
        if(recognition) {
            recognition.lang = currentLang;
            console.log(`Language protocol updated to: ${currentLang}`);
            addMessage('assistant', `Language protocol set to ${langSelect.options[langSelect.selectedIndex].text}.`);
        }
    });

    // --- Initial System Boot ---
    setupVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = setupVoices;
    }
    setupRecognition();
});