/**
 * ALIENX - Conversational Intelligence Assistant
 * Team: ALIENXCODE
 * Frontend Logic: Implements the user-facing components of the architecture.
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

    let isRecording = false;
    let ttsVoices = [];
    
    // --- Component 1: Voice Input Module & Component 2: ASR Engine (Frontend Side) ---
    // Using the browser's Web Speech API which utilizes WebRTC and Google's ASR.
    // This perfectly matches the technology specified in the architecture.
    // -----------------------------------------------------------------------------------
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;

    function setupSpeechRecognition() {
        if (!SpeechRecognition) {
            updateStatus('Voice recognition not supported by this browser.');
            voiceBtn.disabled = true;
            return;
        }
        recognition = new SpeechRecognition();
        recognition.continuous = false; // Stop after first speech pause
        recognition.interimResults = false;
        recognition.lang = 'en-IN'; // Optimized for Indian accents

        recognition.onstart = () => {
            isRecording = true;
            voiceBtn.classList.add('recording');
            updateStatus('Awaiting transmission...');
            updatePipelineStep('input', 'active', 'RECEIVING VOICE');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript.trim();
            addMessage('user', transcript);
            updatePipelineStep('input', 'completed', 'VOICE RECEIVED');
            sendTranscriptToServer(transcript);
        };

        recognition.onend = () => {
            isRecording = false;
            voiceBtn.classList.remove('recording');
            if (statusDiv.textContent === 'Awaiting transmission...') {
                updateStatus('Transmission timed out. System standby.');
                resetPipeline();
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            updateStatus(`Error: ${event.error}. Please check mic permissions.`);
            resetPipeline();
        };
    }
    
    // --- Function to Communicate with the Backend Service ---
    async function sendTranscriptToServer(transcript) {
        if (!transcript) return;
        
        updateStatus('Analyzing transmission...');
        updatePipelineStep('detect', 'active', 'ANALYZING...');

        try {
            const response = await fetch('/process_query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ transcript })
            });

            updatePipelineStep('detect', 'completed', 'LANGUAGE DETECTED');
            updatePipelineStep('core', 'active', 'CORE PROCESSING');

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'A system error occurred.');
            }

            updatePipelineStep('core', 'completed', 'PROCESSING COMPLETE');
            handleServerResponse(data);

        } catch (error) {
            console.error('Server communication error:', error);
            addMessage('assistant', `Error: ${error.message}`);
            updateStatus('Anomaly Detected');
            resetPipeline();
        }
    }

    // --- Function to handle File Upload ---
    async function sendAudioFileToServer(file) {
        if (!file) return;

        addMessage('user', `[Transcribing audio file: ${file.name}]`);
        updateStatus('Uploading and processing audio file...');
        updatePipelineStep('input', 'active', 'UPLOADING FILE');
        
        const formData = new FormData();
        formData.append('audio_file', file);
        
        try {
            const response = await fetch('/upload_audio', {
                method: 'POST',
                body: formData
            });

            updatePipelineStep('input', 'completed', 'UPLOAD COMPLETE');
            updatePipelineStep('detect', 'active', 'ANALYZING...');
            updatePipelineStep('core', 'active', 'CORE PROCESSING');
            
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.response || 'Failed to process audio file.');
            }
            
            updatePipelineStep('core', 'completed', 'PROCESSING COMPLETE');
            handleServerResponse(data);

        } catch(error) {
            console.error('Audio upload error:', error);
            addMessage('assistant', `Error processing file: ${error.message}`);
            updateStatus('File processing failed.');
            resetPipeline();
        }
    }
    
    // --- Functions for Handling AI Response & UI Updates ---
    function handleServerResponse(data) {
        updatePipelineStep('response', 'active', 'GENERATING AUDIO');
        addMessage('assistant', data.response);
        speakResponse(data.response, data.lang);
        
        updatePipelineStep('response', 'completed', 'TRANSMISSION ENDS');
        updateStatus('System ready. Awaiting directive.');
        setTimeout(resetPipeline, 4000);
    }
    
    function speakResponse(text, lang) {
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel(); // Stop any previous speech
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = lang;
            // Find a high-quality local voice if possible
            const voice = ttsVoices.find(v => v.lang === lang && v.localService);
            if (voice) utterance.voice = voice;
            speechSynthesis.speak(utterance);
        }
    }

    const addMessage = (sender, text) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.textContent = text;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    const updateStatus = (message) => statusDiv.textContent = message;
    
    const updatePipelineStep = (stepId, statusClass, message) => {
        const step = document.getElementById(`step-${stepId}`);
        if (step) {
            step.className = `pipeline-step ${statusClass}`;
            step.querySelector('.step-status').textContent = message;
        }
    };
    
    const resetPipeline = () => {
        ['input', 'detect', 'core', 'response'].forEach(id => {
            const defaultText = id === 'input' ? 'STANDBY' : 'AWAITING';
            updatePipelineStep(id, '', defaultText);
        });
    };

    async function clearChat() {
        chatContainer.innerHTML = '';
        addMessage('assistant', 'Dialogue log cleared. Context reset.');
        resetPipeline();
        updateStatus('System ready.');
        try {
            await fetch('/clear_context', { method: 'POST' });
        } catch (error) {
            console.error("Failed to clear server context:", error);
        }
    }

    // --- Event Listeners ---
    voiceBtn.addEventListener('click', () => {
        speechSynthesis.cancel();
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const userText = chatInput.value.trim();
        if (userText) {
            speechSynthesis.cancel();
            updatePipelineStep('input', 'active', 'TEXT INPUT');
            addMessage('user', userText);
            sendTranscriptToServer(userText);
            chatInput.value = '';
        }
    });
    
    audioUploadInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            speechSynthesis.cancel();
            sendAudioFileToServer(file);
        }
        e.target.value = null; // Reset for same-file upload
    });

    clearBtn.addEventListener('click', clearChat);
    
    // --- System Initialization ---
    // Fetch available voices for Text-to-Speech
    function setupVoices() {
      ttsVoices = speechSynthesis.getVoices();
    }
    setupVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = setupVoices;
    }
    
    setupSpeechRecognition(); // Initialize the ASR engine
});