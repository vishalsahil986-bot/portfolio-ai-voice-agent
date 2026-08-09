# AI Voice Agent — Phase 2: Voice Loop Working

The full audio loop now runs end to end: browser mic → WebSocket →
VAD → Whisper STT → dummy reply → ElevenLabs TTS (with 4-account
rotation for Gemini and 3-account rotation for ElevenLabs) → audio
back to the browser. No real "brain" yet — Gemini gets wired in next,
in Phase 3.

## What's here (new/changed since Phase 1)

```
ai_voice_agent/
├── audio/
│   ├── vad.py              # Voice Activity Detection (webrtcvad) — speech_started/speech_ended events
│   ├── audio_buffer.py      # FrameBuffer (slices raw bytes into fixed VAD frames) + UtteranceBuffer
│   └── stt_whisper.py       # Local Whisper STT, transcribes a full utterance
│
├── tts/
│   └── voice_manager.py     # ElevenLabs TTS with automatic key rotation across your 3 accounts
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js               # Mic capture → 16kHz PCM → WebSocket, plays reply audio back
│
├── call/session_manager.py  # (updated) each Session now owns its own VAD + buffers
├── api/websocket_routes.py  # (updated) orchestrates the full pipeline + barge-in handling
├── app.py                   # (updated) now serves frontend/ as static files at "/"
└── requirements.txt          # (updated) webrtcvad, openai-whisper, elevenlabs, numpy
```

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` before this phase actually talks back to you:
- `ELEVENLABS_API_KEYS1/2/3` — your 3 ElevenLabs accounts
- `ELEVENLABS_VOICE_ID` — a voice ID from your ElevenLabs account
- Gemini keys aren't used yet (Phase 3), leave them blank for now

```bash
python main.py
```

Open **http://localhost:8000** in your browser, click **Start Call**,
allow mic access, and talk. When you stop talking (~0.7s of silence),
you should see your transcript appear, then the agent's dummy reply
text, then hear it spoken back in the ElevenLabs voice.

Whisper's model downloads automatically on first use (`base` model,
~150MB) — that first run will pause for a few seconds while it
downloads, then it's cached locally for every run after.

## How the pieces fit together

1. `app.js` captures mic audio, converts it to 16-bit PCM at 16kHz,
   and streams raw bytes over the WebSocket as they're captured.
2. `websocket_routes.py` receives those bytes, and `FrameBuffer`
   (`audio_buffer.py`) slices them into the exact 30ms frames VAD
   requires — the browser's chunk sizes don't need to line up with
   this, `FrameBuffer` absorbs the mismatch.
3. `vad.py` watches the frame stream and fires `speech_started` /
   `speech_ended` once it's confident (3 consecutive speech frames to
   start, ~700ms of silence to end — both tunable in `settings.py`).
4. Everything between those two events gets buffered
   (`UtteranceBuffer`) and handed to `stt_whisper.py` as one clip.
5. The transcribed text gets a dummy reply (`f"You said: {text}"`) —
   this one line is where Gemini plugs in during Phase 3.
6. `voice_manager.py` synthesizes that reply with ElevenLabs, rotating
   through your 3 accounts automatically if one runs out of quota.
7. Both the transcript and the reply audio go back down the same
   WebSocket; `app.js` plays the audio as soon as it arrives.

**Barge-in**: if VAD detects the user speaking again while the agent
is still in the `SPEAKING` state, `call_state_machine.py`'s
`interrupt()` fires immediately, and a reply that's still being
generated gets silently dropped instead of talked over the user. Full
mid-stream audio cancellation (stopping audio that's already playing
in the browser) is a Phase 6 polish item — for now the agent won't
start a NEW reply over you, but a reply already streaming out won't be
yanked back mid-sentence.

## A few things worth knowing before you run it

- **`webrtcvad` + `pkg_resources`**: recent `setuptools` versions
  dropped `pkg_resources`, which `webrtcvad` still imports internally.
  `requirements.txt` pins `setuptools<81` to avoid this breaking on
  install — if you ever see a `pkg_resources` import error, that's why.
- **ElevenLabs + Flash model**: `ELEVENLABS_MODEL_ID` defaults to
  `eleven_flash_v2_5` for low latency. Not every voice supports every
  model — if TTS fails with a compatibility error, check that your
  `ELEVENLABS_VOICE_ID` works with the Flash model in your ElevenLabs
  dashboard.
- **This was tested with Whisper and ElevenLabs mocked out**, since
  the sandbox this was built in can't reach either service. The VAD
  logic, buffering, state machine, rotation logic, and the full
  WebSocket orchestration were all tested for real (including a
  barge-in scenario) — but the first real call *to* Whisper and
  ElevenLabs will be the first time those specific API calls run
  against the real thing. If something doesn't work on your first
  real run, it's most likely on that boundary — start there.

## Next: Phase 3

Replace the dummy `f"You said: {text}"` line in `websocket_routes.py`
with a real Gemini API call, using the `GEMINI_API_KEY1-4` rotation
pool already sitting in `settings.py`.