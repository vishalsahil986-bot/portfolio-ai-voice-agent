const WS_URL = "ws://localhost:8000/ws/call";

const callBtn = document.getElementById("callBtn");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");

let ws = null;
let audioContext = null;
let mediaStream = null;
let processorNode = null;
let sourceNode = null;
let isCallActive = false;

function log(text, cls = "system") {
  const line = document.createElement("div");
  line.className = `log-line ${cls}`;
  line.textContent = text;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}

function floatTo16BitPCM(float32Array) {
  const out = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

async function startCall() {
  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = async () => {
    statusEl.textContent = "Connected — starting mic...";
    await startMic();
  };

  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      handleControlMessage(msg);
    } else {
      // Binary = synthesized reply audio (mp3 bytes) from ElevenLabs
      playReplyAudio(event.data);
    }
  };

  ws.onclose = () => {
    statusEl.textContent = "Disconnected";
    log("WebSocket closed");
    stopCall();
  };

  ws.onerror = (err) => {
    log(`WebSocket error: ${err.message || "connection failed"}`);
  };
}

function handleControlMessage(msg) {
  switch (msg.type) {
    case "session_started":
      statusEl.textContent = `In call (session ${msg.session_id.slice(0, 8)}...)`;
      log("Call connected", "system");
      break;
    case "transcript":
      log(`You: ${msg.text}`, "user");
      break;
    case "reply_text":
      log(`Agent: ${msg.text}`, "agent");
      break;
    case "audio_ack":
      break; // Phase 1 leftover ack, ignored now that the real pipeline is wired in
    default:
      log(`Unknown message: ${JSON.stringify(msg)}`);
  }
}

async function startMic() {
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

  // Requesting a 16000Hz context — the browser resamples the mic
  // input to match, so everything downstream is already at the rate
  // VAD/Whisper expect. (Actual hardware capture rate varies; this is
  // the resampled rate delivered to our processor node.)
  audioContext = new AudioContext({ sampleRate: 16000 });
  sourceNode = audioContext.createMediaStreamSource(mediaStream);

  const bufferSize = 4096;
  processorNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

  processorNode.onaudioprocess = (event) => {
      if (!isCallActive || !ws || ws.readyState !== WebSocket.OPEN) return;
      stopCurrentAudio();  // ← add this line
      const float32 = event.inputBuffer.getChannelData(0);
      const pcm16 = floatTo16BitPCM(float32);
      ws.send(pcm16.buffer);
  };

  sourceNode.connect(processorNode);
  processorNode.connect(audioContext.destination);

  isCallActive = true;
  callBtn.textContent = "End Call";
  callBtn.classList.add("active");
  statusEl.textContent = "Listening...";
}

let currentAudio = null;  // track playing audio globally

function playReplyAudio(arrayBuffer) {
    // Stop any currently playing audio immediately
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.src = "";
        currentAudio = null;
    }

    const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    currentAudio = new Audio(url);
    currentAudio.play().catch((err) => log(`Playback error: ${err.message}`));
    currentAudio.onended = () => {
        URL.revokeObjectURL(url);
        currentAudio = null;
    };
}

// Stop audio when user starts speaking
function stopCurrentAudio() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.src = "";
        currentAudio = null;
    }
}

function stopCall() {
  isCallActive = false;

  if (processorNode) { processorNode.disconnect(); processorNode = null; }
  if (sourceNode) { sourceNode.disconnect(); sourceNode = null; }
  if (audioContext) { audioContext.close(); audioContext = null; }
  if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null; }
  if (ws && ws.readyState === WebSocket.OPEN) { ws.close(); }
  ws = null;

  callBtn.textContent = "Start Call";
  callBtn.classList.remove("active");
  statusEl.textContent = "Not connected";
}

callBtn.addEventListener("click", () => {
  if (isCallActive) {
    stopCall();
  } else {
    logEl.innerHTML = "";
    startCall();
  }
});