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
let currentAudio = null;  // track currently playing audio globally

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

function stopCurrentAudio() {
  // Stop and discard whatever the agent is currently saying
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = "";
    currentAudio = null;
  }
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

    case "stop_audio":
      stopCurrentAudio();
      break;

    case "transcript":
      log(`You: ${msg.text}`, "user");
      break;

    case "reply_text":
      log(`Agent: ${msg.text}`, "agent");
      break;

    case "audio_ack":
      break; // Phase 1 leftover ack, ignored now

    default:
      log(`Unknown message: ${JSON.stringify(msg)}`);
  }
}

async function startMic() {
  mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

  // Requesting a 16000Hz context — the browser resamples the mic
  // input to match, so everything downstream is already at the rate
  // VAD/Whisper expect.
  audioContext = new AudioContext({ sampleRate: 16000 });
  sourceNode = audioContext.createMediaStreamSource(mediaStream);

  const bufferSize = 4096;
  processorNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

  processorNode.onaudioprocess = (event) => {
    if (!isCallActive || !ws || ws.readyState !== WebSocket.OPEN) return;
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

let currentAudio = null;
let audioQueue = [];        // queue of pending audio blobs
let isPlaying = false;      // are we currently playing?

function stopCurrentAudio() {
  // Stop current audio
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.src = "";
    currentAudio = null;
  }
  // Clear the queue — discard all pending answers
  audioQueue = [];
  isPlaying = false;
}

function playReplyAudio(arrayBuffer) {
  // Add to queue — don't play immediately
  audioQueue.push(arrayBuffer);
  // Start playing if nothing is playing right now
  if (!isPlaying) {
    playNext();
  }
}

function playNext() {
  if (audioQueue.length === 0) {
    isPlaying = false;
    return;
  }
  isPlaying = true;
  const arrayBuffer = audioQueue.shift();  // take first item
  const blob = new Blob([arrayBuffer], { type: "audio/mpeg" });
  const url = URL.createObjectURL(blob);
  currentAudio = new Audio(url);
  currentAudio.play().catch((err) => log(`Playback error: ${err.message}`));
  currentAudio.onended = () => {
    URL.revokeObjectURL(url);
    currentAudio = null;
    playNext();  // play next in queue when this finishes
  };
}



function stopCall() {
  isCallActive = false;

  audioQueue = [];     
  isPlaying = false;
  stopCurrentAudio();

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

