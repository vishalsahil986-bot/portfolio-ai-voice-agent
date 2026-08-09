# AI Voice Agent — Phase 1: Backend Skeleton

This is the foundation. No AI logic yet (no STT, no Gemini, no ElevenLabs,
no RAG) — the goal of this phase is a backend that **starts correctly,
accepts a real-time connection, tracks sessions and call state, and
shuts down cleanly.** Everything else gets built on top of this without
having to touch it again.

## What's here

```
ai_voice_agent/
├── main.py                    # run this to start the server
├── app.py                     # FastAPI app + router wiring
├── requirements.txt
├── .env.example                # copy to .env and fill in
│
├── config/
│   └── settings.py            # all config/secrets, loaded from .env
│
├── call/
│   ├── call_state_machine.py  # LISTENING / THINKING / SPEAKING + interrupt()
│   └── session_manager.py     # one Session per active connection
│
├── api/
│   ├── health_routes.py       # GET /health
│   └── websocket_routes.py    # WS /ws/call — the audio pipe (no STT yet)
│
└── utils/
    └── logger.py
```

## Why the state machine matters

`call_state_machine.py` is the piece worth understanding before Phase 2,
because it encodes the turn-taking rule from the spec:

- `LISTENING` → `THINKING` → `SPEAKING` → `LISTENING` is the normal loop.
- `interrupt()` can force **any** state back to `LISTENING` immediately —
  this is what will stop TTS mid-sentence when the user starts talking
  (barge-in). It's tested and working already; Phase 6 just has to call
  it from the VAD.
- Invalid transitions (e.g. `LISTENING` → `SPEAKING` directly) raise
  `InvalidTransition` instead of silently doing the wrong thing.

## Running it

```bash
cp .env.example .env          # fill in real keys later, not needed for Phase 1
pip install -r requirements.txt
python main.py
```

Server runs at `http://localhost:8000`.

- `GET /health` → `{"status": "ok"}`
- `WS /ws/call` → accepts the connection, sends back `session_started`
  with a session id, then echoes an `audio_ack` for every binary chunk
  you send it. This is what your website's mic-capture code will talk
  to in Phase 2.

Both were tested manually while building this: health check returns
200, and a WebSocket client that connects, sends fake audio bytes, and
disconnects gets a clean session lifecycle in the logs (created →
audio received → disconnected → session ended).

## What's NOT here yet (by design)

- No VAD, no Whisper STT, no Gemini calls, no ElevenLabs TTS, no RAG,
  no memory. The `/ws/call` endpoint just acknowledges audio bytes —
  it doesn't understand them yet.
- No key-rotation logic for your 3 ElevenLabs accounts yet — but
  `ELEVENLABS_API_KEYS` in `.env`/`settings.py` is already set up as a
  comma-separated pool, ready for `tts/voice_manager.py` in Phase 2 to
  rotate through on quota errors.

## Next: Phase 2

Wire the real audio loop: browser mic → WebSocket (already built) →
VAD → Whisper STT → (dummy echo response for now) → ElevenLabs TTS
(with the account-rotation wrapper) → audio back to the browser. Once
you can talk to it and hear a voice respond, Phase 3 swaps the dummy
response for real Gemini calls.