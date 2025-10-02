/**
 * Audio processing client for bidirectional audio AI communication
 * Adapted from NavigoAI for Agent Connect Server
 */

class SoundHandler {
    constructor(serverUrl = 'ws://localhost:8080') {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.recorder = null;
        this.audioContext = null;
        this.isConnected = false;
        this.isRecording = false;
        this.isModelSpeaking = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.userId = null;

        // Callbacks
        this.onReady = () => { };
        this.onAudioReceived = () => { };
        this.onTextReceived = () => { };
        this.onUserTranscript = () => { };
        this.onTurnComplete = () => { };
        this.onError = () => { };
        this.onInterrupted = () => { };

        // Audio playback
        this.audioQueue = [];
        this.isPlaying = false;
        this.currentSource = null;

        // Clean up any existing audioContexts
        if (window.existingAudioContexts) {
            window.existingAudioContexts.forEach(ctx => {
                try {
                    ctx.close();
                } catch (e) {
                    console.error("Error closing existing audio context:", e);
                }
            });
        }

        // Keep track of audio contexts created
        window.existingAudioContexts = window.existingAudioContexts || [];
    }

    // Set user ID for connection
    setUserId(userId) {
        this.userId = userId;
    }

    // Connect to the WebSocket server
    async openConnection() {
        if (!this.userId) {
            throw new Error('User ID must be set before connecting');
        }

        // Close existing connection if any
        if (this.ws) {
            try {
                this.ws.close();
            } catch (e) {
                console.error("Error closing WebSocket:", e);
            }
        }

        return new Promise((resolve, reject) => {
            try {
                const wsUrl = `${this.serverUrl}/agent/ws/${this.userId}?is_audio=true`;
                console.log('Connecting to:', wsUrl);
                this.ws = new WebSocket(wsUrl);

                const connectionTimeout = setTimeout(() => {
                    if (!this.isConnected) {
                        console.error('Connection timed out');
                        reject(new Error('Connection timeout'));
                    }
                }, 10000);

                this.ws.onopen = () => {
                    console.log('Connection established');
                    clearTimeout(connectionTimeout);
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.onReady();
                    resolve();
                };

                this.ws.onclose = (event) => {
                    console.log('Connection closed:', event.code, event.reason);
                    this.isConnected = false;

                    // Try to reconnect if it wasn't a normal closure
                    if (event.code !== 1000 && event.code !== 1001 && this.maxReconnectAttempts > 0) {
                        this.attemptReconnect();
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('Connection error:', error);
                    clearTimeout(connectionTimeout);
                    this.onError(error);
                    reject(error);
                };

                this.ws.onmessage = async (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        await this.handleMessage(message);
                    } catch (error) {
                        console.error('Error handling message:', error);
                    }
                };
            } catch (error) {
                console.error('Error creating connection:', error);
                reject(error);
            }
        });
    }

    // Handle incoming messages
    async handleMessage(message) {
        // Handle error messages
        if (message.error) {
            this.onError(message.error);
            return;
        }

        // Handle turn completion
        if (message.turn_complete === true) {
            this.isModelSpeaking = false;
            this.onTurnComplete();
            return;
        }

        // Handle interruption
        if (message.interrupted === true) {
            this.isModelSpeaking = false;
            this.onInterrupted();
            return;
        }

        // Handle different MIME types
        if (message.mime_type === 'audio/pcm') {
            this.onAudioReceived(message.data);
            await this.playSound(message.data);
        } else if (message.mime_type === 'text/plain') {
            this.onTextReceived(message.data);
        }
    }

    // Try to reconnect with exponential backoff
    async attemptReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const backoffTime = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);

        console.log(`Reconnecting in ${backoffTime}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(async () => {
            try {
                await this.openConnection();
                console.log('Reconnected successfully');
            } catch (error) {
                console.error('Reconnection failed:', error);
            }
        }, backoffTime);
    }

    // Initialize the audio context and recorder
    async setupAudio() {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Reuse existing audio context if available or create a new one
            if (!this.audioContext || this.audioContext.state === 'closed') {
                console.log("Creating new sound context");
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 16000 // Match the sample rate expected by server
                });

                // Track this context for cleanup
                window.existingAudioContexts = window.existingAudioContexts || [];
                window.existingAudioContexts.push(this.audioContext);
            }

            // Create MediaStreamSource
            const source = this.audioContext.createMediaStreamSource(stream);

            // Create ScriptProcessor for audio processing
            const processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            processor.onaudioprocess = (e) => {
                if (!this.isRecording) return;

                // Get audio data
                const inputData = e.inputBuffer.getChannelData(0);

                // Convert float32 to int16
                const int16Data = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    int16Data[i] = Math.max(-32768, Math.min(32767, Math.floor(inputData[i] * 32768)));
                }

                // Send to server if connected
                if (this.isConnected && this.isRecording) {
                    const audioBuffer = new Uint8Array(int16Data.buffer);
                    const base64Audio = this._arrayBufferToBase64(audioBuffer);

                    this.ws.send(JSON.stringify({
                        mime_type: 'audio/pcm',
                        data: base64Audio
                    }));
                }
            };

            // Connect the audio nodes
            source.connect(processor);
            processor.connect(this.audioContext.destination);

            this.recorder = {
                source: source,
                processor: processor,
                stream: stream
            };

            return true;
        } catch (error) {
            console.error('Error setting up audio:', error);
            this.onError(error);
            return false;
        }
    }

    // Start recording audio
    async start() {
        if (!this.recorder) {
            const initialized = await this.setupAudio();
            if (!initialized) return false;
        }

        if (!this.isConnected) {
            try {
                await this.openConnection();
            } catch (error) {
                console.error('Failed to open connection:', error);
                return false;
            }
        }

        this.isRecording = true;
        return true;
    }

    // Stop recording audio
    stop() {
        this.isRecording = false;
    }

    // Decode and play received audio
    async playSound(base64Audio) {
        try {
            // Decode the base64 audio data
            const audioData = this._base64ToArrayBuffer(base64Audio);

            // Create an audio context if needed
            if (!this.audioContext || this.audioContext.state === 'closed') {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 24000 // Match the sample rate received from server
                });

                // Track this context for cleanup
                window.existingAudioContexts.push(this.audioContext);

                // Limit the number of contexts we track to avoid memory issues
                if (window.existingAudioContexts.length > 5) {
                    const oldContext = window.existingAudioContexts.shift();
                    try {
                        if (oldContext && oldContext !== this.audioContext && oldContext.state !== 'closed') {
                            oldContext.close();
                        }
                    } catch (e) {
                        console.error("Error closing old audio context:", e);
                    }
                }
            }

            // Resume audio context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            // Add to audio queue
            this.audioQueue.push(audioData);

            // If not currently playing, start playback
            if (!this.isPlaying) {
                this.playNext();
            }

            // Set flag to indicate model is speaking
            this.isModelSpeaking = true;
        } catch (error) {
            console.error('Error playing sound:', error);
        }
    }

    // Play next audio chunk from queue
    playNext() {
        if (this.audioQueue.length === 0) {
            this.isPlaying = false;
            return;
        }

        this.isPlaying = true;

        try {
            // Stop any previous source if still active
            if (this.currentSource) {
                try {
                    this.currentSource.onended = null; // Remove event listener
                    this.currentSource.stop();
                    this.currentSource.disconnect();
                } catch (e) {
                    // Ignore errors if already stopped
                }
                this.currentSource = null;
            }

            // Get next audio data from queue
            const audioData = this.audioQueue.shift();

            // Convert Int16Array to Float32Array for AudioBuffer
            const int16Array = new Int16Array(audioData);
            const float32Array = new Float32Array(int16Array.length);
            for (let i = 0; i < int16Array.length; i++) {
                float32Array[i] = int16Array[i] / 32768.0;
            }

            // Create an AudioBuffer
            const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, 24000);
            audioBuffer.getChannelData(0).set(float32Array);

            // Create a source node
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;

            // Store reference to current source
            this.currentSource = source;

            // Connect to destination
            source.connect(this.audioContext.destination);

            // When this buffer ends, play the next one
            source.onended = () => {
                this.currentSource = null;
                this.playNext();
            };

            // Start playing
            source.start(0);
        } catch (error) {
            console.error('Error during sound playback:', error);
            this.currentSource = null;
            // Try next buffer on error
            setTimeout(() => this.playNext(), 100);
        }
    }

    // Interrupt current playback
    interrupt() {
        this.isModelSpeaking = false;

        // Stop current audio source if active
        if (this.currentSource) {
            try {
                this.currentSource.onended = null; // Remove event listener
                this.currentSource.stop();
                this.currentSource.disconnect();
            } catch (e) {
                // Ignore errors if already stopped
            }
            this.currentSource = null;
        }

        // Clear queue and reset playing state
        this.audioQueue = [];
        this.isPlaying = false;
    }

    // Cleanup resources
    closeConnection() {
        this.stop();

        // Stop any audio playback
        this.interrupt();
        this.isModelSpeaking = false;

        // Clean up recorder
        if (this.recorder) {
            try {
                this.recorder.stream.getTracks().forEach(track => track.stop());
                this.recorder.source.disconnect();
                this.recorder.processor.disconnect();
                this.recorder = null;
            } catch (e) {
                console.error("Error cleaning up recorder:", e);
            }
        }

        // Close audio context
        if (this.audioContext && this.audioContext.state !== 'closed') {
            try {
                this.audioContext.close().catch(e => console.error("Error closing audio context:", e));
            } catch (e) {
                console.error("Error closing audio context:", e);
            }
        }

        // Close WebSocket
        if (this.ws) {
            try {
                if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
                    this.ws.close();
                }
                this.ws = null;
            } catch (e) {
                console.error("Error closing WebSocket:", e);
            }
        }

        this.isConnected = false;
    }

    // Utility: Convert ArrayBuffer to Base64
    _arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;
        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    // Utility: Convert Base64 to ArrayBuffer
    _base64ToArrayBuffer(base64) {
        const binaryString = atob(base64);
        const len = binaryString.length;
        const bytes = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return bytes.buffer;
    }
}
