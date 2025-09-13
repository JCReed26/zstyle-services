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
 * app.js: JS code for the adk-streaming sample app.
 */

/**
 * WebSocket handling
 */

// Connect the server with a WebSocket connection
const urlParams = new URLSearchParams(window.location.search);
const userId = urlParams.get('user_id');

let websocket = null;
let is_audio = false;
let isClosing = false;
let isConnecting = false; // Prevent multiple simultaneous connections

// Connection resilience variables
let reconnectAttempts = 0;
let maxReconnectAttempts = 10;
let baseDelay = 1000; // Start with 1 second
let maxDelay = 60000; // Cap at 60 seconds
let circuitBreakerTimeout = 300000; // 5 minutes
let isCircuitBreakerOpen = false;
let lastConnectionAttempt = 0;
let consecutiveFailures = 0;
let reconnectTimer = null; // Track reconnection timer

// Get DOM elements
const messageForm = document.getElementById("messageForm");
const messageInput = document.getElementById("message");
const messagesDiv = document.getElementById("messages");
let currentMessageId = null;

// Gracefully close the websocket connection on page unload
window.onbeforeunload = function() {
    if (websocket) {
        isClosing = true;
        websocket.close();
    }
};

// WebSocket handlers
function connectWebsocket() {
  // Prevent multiple simultaneous connections
  if (isConnecting) {
    console.log("Connection already in progress, skipping");
    return;
  }

  // Check circuit breaker
  if (isCircuitBreakerOpen) {
    const timeSinceLastAttempt = Date.now() - lastConnectionAttempt;
    if (timeSinceLastAttempt < circuitBreakerTimeout) {
      console.log(`Circuit breaker open. Next attempt in ${Math.ceil((circuitBreakerTimeout - timeSinceLastAttempt) / 1000)} seconds`);
      document.getElementById("messages").textContent = `Connection temporarily disabled. Retrying in ${Math.ceil((circuitBreakerTimeout - timeSinceLastAttempt) / 1000)} seconds...`;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(connectWebsocket, 10000); // Check every 10 seconds
      return;
    } else {
      // Reset circuit breaker
      isCircuitBreakerOpen = false;
      consecutiveFailures = 0;
      reconnectAttempts = 0;
      console.log("Circuit breaker reset, attempting connection");
    }
  }

  // Clear any existing reconnect timer
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  // Close existing connection if it exists
  if (websocket && websocket.readyState !== WebSocket.CLOSED) {
    console.log("Closing existing connection before creating new one");
    isClosing = true;
    websocket.close();
    websocket = null;
  }

  // Reset flags
  isClosing = false;
  isConnecting = true;
  lastConnectionAttempt = Date.now();

  if (!userId) {
    alert("User ID not found. Please log in.");
    window.location.href = 'index.html';
    isConnecting = false;
    return;
  }

  const ws_url = `ws://${window.location.host}/agent/ws/${userId}?is_audio=${is_audio}`;
  console.log("ws_url: " + ws_url);
  console.log(`Connection attempt ${reconnectAttempts + 1}/${maxReconnectAttempts}`);

  // Update UI with connection status
  document.getElementById("messages").textContent = `Connecting... (attempt ${reconnectAttempts + 1})`;

  try {
    // Connect websocket
    websocket = new WebSocket(ws_url);

    // Handle connection open
    websocket.onopen = function () {
      console.log("WebSocket connection opened.");
      document.getElementById("messages").textContent = "Connection opened";
      isConnecting = false;

      // Reset connection tracking on success
      reconnectAttempts = 0;
      consecutiveFailures = 0;
      isCircuitBreakerOpen = false;

      // Enable the Send button
      document.getElementById("sendButton").disabled = false;
      addSubmitHandler();
    };
  } catch (error) {
    console.error("Error creating WebSocket:", error);
    isConnecting = false;
    handleConnectionFailure();
    return;
  }

  // Handle incoming messages
  websocket.onmessage = function (event) {
    const message_from_server = JSON.parse(event.data);
    console.log("[AGENT TO CLIENT] ", message_from_server);

    // Check for error messages and handle them
    if (message_from_server.error) {
      console.error("Server error:", message_from_server.error);
      handleConnectionError(message_from_server.error);
      return;
    }

    // Check if the turn is complete
    if (
      message_from_server.turn_complete &&
      message_from_server.turn_complete == true
    ) {
      currentMessageId = null;
      return;
    }

    // Check for interrupt message
    if (
      message_from_server.interrupted &&
      message_from_server.interrupted === true
    ) {
      // Stop audio playback if it's playing
      if (audioPlayerNode) {
        audioPlayerNode.port.postMessage({ command: "endOfAudio" });
      }
      return;
    }

    // If it's audio, play it
    if (message_from_server.mime_type == "audio/pcm" && audioPlayerNode) {
      audioPlayerNode.port.postMessage(base64ToArray(message_from_server.data));
    }

    // If it's a text, print it
    if (message_from_server.mime_type == "text/plain") {
      // add a new message for a new turn
      if (currentMessageId == null) {
        currentMessageId = Math.random().toString(36).substring(7);
        const message = document.createElement("p");
        message.id = currentMessageId;
        // Append the message element to the messagesDiv
        messagesDiv.appendChild(message);
      }

      // Add message text to the existing message element
      const message = document.getElementById(currentMessageId);
      message.textContent += message_from_server.data;

      // Scroll down to the bottom of the messagesDiv
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
  };

  // Handle connection close
  websocket.onclose = function (event) {
    console.log("WebSocket connection closed.", event.code, event.reason);
    document.getElementById("sendButton").disabled = true;
    isConnecting = false;
    
    // Don't reconnect if we are intentionally closing
    if (isClosing) {
      document.getElementById("messages").textContent = "Connection closed";
      return;
    }

    handleConnectionFailure();
  };

  websocket.onerror = function (e) {
    console.log("WebSocket error: ", e);
    isConnecting = false;
    handleConnectionFailure();
  };
}

// Handle connection errors from server messages
function handleConnectionError(errorMessage) {
  console.error("Connection error:", errorMessage);
  
  // Check if it's a rate limiting error
  if (errorMessage.includes("429") || errorMessage.includes("rate limit") ||
      errorMessage.includes("Too many connection attempts") || 
      errorMessage.includes("Service is busy")) {
    // Force circuit breaker open for rate limiting
    isCircuitBreakerOpen = true;
    consecutiveFailures = 5; // Trigger circuit breaker
    console.log("Server-side rate limiting detected, opening circuit breaker");
    document.getElementById("messages").textContent = errorMessage;
    return; // Don't call handleConnectionFailure to avoid immediate retry
  }
  
  handleConnectionFailure();
}

// Handle connection failures with exponential backoff and circuit breaker
function handleConnectionFailure() {
  consecutiveFailures++;
  reconnectAttempts++;

  // Clear any existing reconnect timer
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  // Open circuit breaker after too many consecutive failures
  if (consecutiveFailures >= 5) {
    isCircuitBreakerOpen = true;
    console.log("Circuit breaker opened due to consecutive failures");
    document.getElementById("messages").textContent = "Connection issues detected. Pausing reconnection attempts...";
    reconnectTimer = setTimeout(connectWebsocket, circuitBreakerTimeout);
    return;
  }

  // Stop trying after max attempts
  if (reconnectAttempts >= maxReconnectAttempts) {
    console.log("Max reconnection attempts reached");
    document.getElementById("messages").textContent = "Connection failed. Please refresh the page to try again.";
    return;
  }

  // Calculate exponential backoff delay
  const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts - 1), maxDelay);
  
  console.log(`Reconnecting in ${delay / 1000} seconds... (attempt ${reconnectAttempts}/${maxReconnectAttempts})`);
  document.getElementById("messages").textContent = `Connection lost. Reconnecting in ${delay / 1000} seconds...`;

  reconnectTimer = setTimeout(connectWebsocket, delay);
}

connectWebsocket();

// Add submit handler to the form
function addSubmitHandler() {
  messageForm.onsubmit = function (e) {
    e.preventDefault();
    const message = messageInput.value;
    if (message) {
      const p = document.createElement("p");
      p.textContent = "> " + message;
      messagesDiv.appendChild(p);
      messageInput.value = "";
      sendMessage({
        mime_type: "text/plain",
        data: message,
      });
      console.log("[CLIENT TO AGENT] " + message);
    }
    return false;
  };
}

// Send a message to the server as a JSON string
function sendMessage(message) {
  if (websocket && websocket.readyState == WebSocket.OPEN) {
    const messageJson = JSON.stringify(message);
    websocket.send(messageJson);
  }
}

// Decode Base64 data to Array
function base64ToArray(base64) {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

/**
 * Audio handling
 */

let audioPlayerNode;
let audioPlayerContext;
let audioRecorderNode;
let audioRecorderContext;
let micStream;
let isRecording = false;

// Audio buffering for 0.2s intervals
let audioBuffer = [];
let bufferTimer = null;

// Import the audio worklets
import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet } from "./audio-recorder.js";

// Start audio
function startAudio() {
  // Reset connection state when starting audio
  isClosing = false;
  isRecording = true;
  
  // Start audio output
  startAudioPlayerWorklet().then(([node, ctx]) => {
    audioPlayerNode = node;
    audioPlayerContext = ctx;
  });
  // Start audio input
  startAudioRecorderWorklet(audioRecorderHandler).then(
    ([node, ctx, stream]) => {
      audioRecorderNode = node;
      audioRecorderContext = ctx;
      micStream = stream;
    }
  );
}

// Start the audio only when the user clicked the button
// (due to the gesture requirement for the Web Audio API)
const startAudioButton = document.getElementById("startAudioButton");
startAudioButton.addEventListener("click", () => {
  startAudioButton.disabled = true;
  stopAudioButton.disabled = false;
  
  // Reset connection state before starting audio
  isClosing = false;
  reconnectAttempts = 0;
  consecutiveFailures = 0;
  isCircuitBreakerOpen = false;
  
  startAudio();
  is_audio = true;
  connectWebsocket(); // reconnect with the audio mode
});

const stopAudioButton = document.getElementById("stopAudioButton");
stopAudioButton.addEventListener("click", stopAudio);

function stopAudio() {
  isRecording = false; // Immediately stop recording
  stopAudioRecording(); // Stop the recording/sending loop
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
  }
  if (websocket) {
    isClosing = true;
    websocket.close();
  }
  is_audio = false;
  startAudioButton.disabled = false;
  stopAudioButton.disabled = true;
}

// Audio recorder handler
function audioRecorderHandler(pcmData) {
  // Add audio data to buffer
  audioBuffer.push(new Uint8Array(pcmData));
  
  // Start timer if not already running
  if (!bufferTimer) {
    bufferTimer = setInterval(sendBufferedAudio, 200); // 0.2 seconds
  }
}

// Send buffered audio data every 0.2 seconds
function sendBufferedAudio() {
  if (audioBuffer.length === 0 || !isRecording) {
    return;
  }
  
  // Calculate total length
  let totalLength = 0;
  for (const chunk of audioBuffer) {
    totalLength += chunk.length;
  }
  
  // Combine all chunks into a single buffer
  const combinedBuffer = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of audioBuffer) {
    combinedBuffer.set(chunk, offset);
    offset += chunk.length;
  }
  
  // Send the combined audio data
  sendMessage({
    mime_type: "audio/pcm",
    data: arrayBufferToBase64(combinedBuffer.buffer),
  });
  console.log("[CLIENT TO AGENT] sent %s bytes", combinedBuffer.byteLength);
  
  // Clear the buffer
  audioBuffer = [];
}

// Stop audio recording and cleanup
function stopAudioRecording() {
  if (bufferTimer) {
    clearInterval(bufferTimer);
    bufferTimer = null;
  }
  // Clear the buffer to prevent any lingering data from being sent
  audioBuffer = [];
}

// Encode an array buffer with Base64
function arrayBufferToBase64(buffer) {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
