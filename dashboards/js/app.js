/**
* Copyright 2025 Google LLC
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

/**
 * app.js: Simplified WebSocket client using StreamManager
 * Based on NavigoAI implementation for stable connection handling
 */

// Get user ID from URL parameters
const urlParams = new URLSearchParams(window.location.search);
const userId = urlParams.get('user_id');

if (!userId) {
    alert("User ID not found. Please log in.");
    window.location.href = 'index.html';
}

// Initialize StreamManager
const stream = new StreamManager();
stream.setUserId(userId);
stream.maxReconnectAttempts = 3; // Enable limited reconnection

// Get DOM elements
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("message");
const messagesDiv = document.getElementById("messages");
const startAudioButton = document.getElementById("startAudioButton");
const stopAudioButton = document.getElementById("stopAudioButton");
const sendButton = document.getElementById("sendButton");

// State variables
let currentMessageId = null;
let isAudioMode = false;
let currentResponseText = '';
let isFirstChunk = true;

// Initialize the connection
async function initializeConnection() {
    try {
        await stream.openConnection();
        
        // Set up event handlers
        stream.onReady = () => {
            console.log('Stream ready');
            messagesDiv.textContent = "Connected to agent";
            if (sendButton) sendButton.disabled = false;
            addSubmitHandler();
        };

        stream.onTextReceived = (text) => {
            if (text && text.trim()) {
                if (isFirstChunk) {
                    currentResponseText = text;
                    addMessage(text, 'assistant', true);
                    isFirstChunk = false;
                } else {
                    currentResponseText += text;
                    updateMessage(currentMessageId, currentResponseText, true);
                }
            }
        };

        stream.onTurnComplete = () => {
            console.log('Turn complete');
            if (currentMessageId) {
                updateMessage(currentMessageId, currentResponseText, false);
            }
            currentResponseText = '';
            isFirstChunk = true;
            currentMessageId = null;
        };

        stream.onError = (error) => {
            console.error('Stream error:', error);
            messagesDiv.textContent = `Error: ${error}`;
        };

        stream.onInterrupted = () => {
            console.log('Stream interrupted');
            stream.interrupt();
            currentResponseText = '';
            isFirstChunk = true;
            currentMessageId = null;
        };

    } catch (error) {
        console.error('Failed to initialize connection:', error);
        messagesDiv.textContent = "Connection failed. Please refresh the page.";
    }
}

// Add message to the chat
function addMessage(text, sender, isPartial = false) {
    // Remove initial placeholder if it exists
    const placeholder = messagesDiv.querySelector('.text-center');
    if (placeholder) {
        placeholder.remove();
    }

    const messageElement = document.createElement("p");
    currentMessageId = Math.random().toString(36).substring(7);
    messageElement.id = currentMessageId;
    
    if (sender === 'user') {
        messageElement.textContent = "> " + text;
        messageElement.style.color = "#1a73e8";
    } else {
        messageElement.textContent = text;
        messageElement.style.color = "#202124";
    }
    
    if (isPartial) {
        messageElement.style.opacity = "0.7";
    }
    
    messagesDiv.appendChild(messageElement);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return currentMessageId;
}

// Update existing message
function updateMessage(messageId, text, isPartial = false) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.textContent = text;
        messageElement.style.opacity = isPartial ? "0.7" : "1";
    }
}

// Send text message
function sendMessage(message) {
    if (stream.isConnected) {
        stream.ws.send(JSON.stringify({
            mime_type: "text/plain",
            data: message
        }));
    }
}

// Add submit handler for text messages
function addSubmitHandler() {
    if (messageForm) {
        messageForm.onsubmit = function (e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message) {
                addMessage(message, 'user');
                messageInput.value = "";
                sendMessage(message);
                console.log("[CLIENT TO AGENT] " + message);
            }
            return false;
        };
    }
}

// Audio button handlers
if (startAudioButton) {
    startAudioButton.addEventListener("click", async () => {
        try {
            const success = await stream.start();
            if (success) {
                isAudioMode = true;
                startAudioButton.disabled = true;
                stopAudioButton.disabled = false;
                messagesDiv.textContent = "Audio mode active - speak now";
            }
        } catch (error) {
            console.error('Error starting audio:', error);
            messagesDiv.textContent = "Error starting audio. Please try again.";
        }
    });
}

if (stopAudioButton) {
    stopAudioButton.addEventListener("click", () => {
        stream.stop();
        isAudioMode = false;
        startAudioButton.disabled = false;
        stopAudioButton.disabled = true;
        messagesDiv.textContent = "Audio mode stopped";
    });
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stream.closeConnection();
});

// Initialize on page load
window.addEventListener('load', () => {
    initializeConnection();
});

// Decode Base64 data to Array (kept for compatibility)
function base64ToArray(base64) {
    const binaryString = window.atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
}

// Encode an array buffer with Base64 (kept for compatibility)
function arrayBufferToBase64(buffer) {
    let binary = "";
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}
