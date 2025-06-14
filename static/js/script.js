document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const voiceBtn = document.getElementById('voiceBtn');
    const statusDiv = document.getElementById('status');
    const chatContainer = document.getElementById('chatContainer');
    const clearBtn = document.getElementById('clearBtn');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const audioUploadInput = document.getElementById('audioUploadInput');
    
    let isRecording = false;
    let ttsVoices = [];
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    // --- Core Functions ---
    const setupVoices = () => {
        ttsVoices = speechSynthesis.getVoices();
    };
    
    const setupRecognition = () => {
        if (!SpeechRecognition) {
            statusDiv.textContent = 'Voice recognition not supported by browser.';
            voiceBtn.disabled = true;
            return;
        }
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        // This dynamically sets language, though backend detection is now primary
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isRecording = true;
            voiceBtn.classList.add('recording');
            updateStatus('Awaiting transmission...');
            updatePipelineStep('input', 'active', 'RECEIVING');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            updatePipelineStep('input', 'completed', 'VOICE');
            processTranscript(transcript.trim());
        };

        recognition.onend = () => {
            isRecording = false;
            voiceBtn.classList.remove('recording');
            if (statusDiv.textContent === 'Awaiting transmission...') {
                updateStatus('Transmission timed out.');
                resetPipeline();
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            updateStatus(`Error: ${event.error}.`);
            resetPipeline();
        };
    };
    
    const handleServerResponse = async (responsePromise, inputType) => {
        try {
            updatePipelineStep('detect', 'active', 'ANALYZING');
            const res = await responsePromise;

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ response: 'Unknown server error.' }));
                // Use the server's error message if available
                throw new Error(errData.response || errData.error || `Server error: ${res.status}`);
            }
            
            updatePipelineStep('detect', 'completed', 'DETECTED');
            updatePipelineStep('core', 'active', 'PROCESSING');
            
            const data = await res.json();
            
            updatePipelineStep('core', 'completed', 'COMPLETE');
            updatePipelineStep('response', 'active', 'GENERATING');

            addMessage('assistant', data.response);
            speakResponse(data.response, data.lang);

            updatePipelineStep('response', 'completed', 'COMPLETE');
            updateStatus('System ready. Awaiting directive.');

            setTimeout(resetPipeline, 4000);

        } catch (error) {
            console.error('Error processing request:', error);
            const errorMessage = error.message || "Connection to core matrix disrupted.";
            addMessage('assistant', errorMessage);
            updateStatus('Anomaly Detected');
            resetPipeline();
        }
    };
    
    const processTranscript = (transcript) => {
        addMessage('user', transcript);
        updateStatus('Analyzing transmission...');
        updatePipelineStep('input', 'completed', 'TEXT/VOICE');

        const promise = fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript })
        });
        handleServerResponse(promise);
    };

    const processAudioFile = (file) => {
        addMessage('user', `[Uploaded File: ${file.name}]`);
        updateStatus('Uploading and transcribing...');
        updatePipelineStep('input', 'active', 'UPLOADING');

        const formData = new FormData();
        formData.append('audio_file', file);

        const promise = fetch('/upload_audio', {
            method: 'POST',
            body: formData
        });
        handleServerResponse(promise);
    };
    
    const speakResponse = (text, lang) => {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang;
            const voice = ttsVoices.find(v => v.lang === lang);
            if (voice) {
                utterance.voice = voice;
            } else {
                console.warn(`TTS voice for lang '${lang}' not found.`);
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
        const step = document.getElementById(`step-${stepId}`);
        if(step) {
            step.className = `pipeline-step ${status}`;
            step.querySelector('.step-status').textContent = message;
        }
    };
    const resetPipeline = () => {
        ['input', 'detect', 'core', 'response'].forEach(id => 
            updatePipelineStep(id, '', id === 'input' ? 'STANDBY' : 'AWAITING')
        );
    };

    const clearChat = async () => {
        chatContainer.innerHTML = '';
        addMessage('assistant', 'Log cleared. Awaiting new directive.');
        resetPipeline();
        updateStatus('System ready.');
        try {
            await fetch('/clear', { method: 'POST' });
            console.log("Server history cleared.");
        } catch (error) {
            console.error("Failed to clear server history:", error);
        }
    };
    
    // --- Event Listeners ---
    voiceBtn.addEventListener('click', () => {
        if (speechSynthesis.speaking) speechSynthesis.cancel();
        if (recognition) {
            isRecording ? recognition.stop() : recognition.start();
        }
    });
    
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const userText = chatInput.value.trim();
        if(userText) {
            if (speechSynthesis.speaking) speechSynthesis.cancel();
            updatePipelineStep('input', 'active', 'TEXT');
            processTranscript(userText);
            chatInput.value = '';
        }
    });

    audioUploadInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (speechSynthesis.speaking) speechSynthesis.cancel();
            processAudioFile(file);
        }
        // Reset the input so the same file can be uploaded again
        e.target.value = null; 
    });

    clearBtn.addEventListener('click', clearChat);
    
    // Interrupt speech on any click that isn't on a primary control
    document.addEventListener('click', (event) => {
        const controls = [voiceBtn, clearBtn, audioUploadInput, chatInput, chatForm.querySelector('button')];
        // Check if the click target or its parent is one of the controls
        if (!controls.some(control => control.contains(event.target))) {
             if (speechSynthesis.speaking) {
                speechSynthesis.cancel();
            }
        }
    });

    // --- Initial System Boot ---
    setupVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = setupVoices;
    }
    setupRecognition();
});