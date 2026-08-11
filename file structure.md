ai_voice_agent/
├── main.py                    ✅ entry point
├── app.py                     ✅ FastAPI app, static frontend mount
├── requirements.txt           ✅
├── .env.example                ✅
├── README.md                  ✅
│
├── config/
│   ├── __init__.py             ✅
│   └── settings.py            ✅ Gemini keys 1-4, ElevenLabs keys 1-3, all config
│
├── call/
│   ├── __init__.py             ✅
│   ├── call_state_machine.py  ✅ LISTENING/THINKING/SPEAKING + interrupt()
│   └── session_manager.py     ✅ per-connection session + audio state
│
├── audio/
│   ├── __init__.py             ✅
│   ├── vad.py                 ✅ speech_started/speech_ended detection
│   ├── audio_buffer.py        ✅ FrameBuffer + UtteranceBuffer
│   └── stt_whisper.py         ✅ local Whisper transcription
│
├── tts/
│   ├── __init__.py             ✅
│   └── voice_manager.py       ✅ ElevenLabs + key rotation
│
├── api/
│   ├── __init__.py             ✅
│   ├── health_routes.py       ✅ GET /health
│   └── websocket_routes.py    ✅ WS /ws/call — full pipeline orchestration
│
├── frontend/
│   ├── index.html              ✅
│   ├── style.css               ✅
│   └── app.js                  ✅ mic capture → PCM → WebSocket → playback
│
├── utils/
│   ├── __init__.py             ✅
│   └── logger.py              ✅
│
├── llm/                                          ✅ PHASE 3
│   ├── __init__.py
│   ├── gemini_service.py      ✅ Gemini calls, rotates GEMINI_API_KEY1-4
│   └── prompt_builder.py      ✅ builds system prompt + conversation turn
│
├── rag/                                          ✅ PHASE 4
│   ├── __init__.py
│   ├── vector_store.py        ✅ embeddings index (FAISS/Chroma)
│   ├── ingest.py               ✅✅ chunk + embed source documents
│   └── retriever.py            ✅ pulls relevant chunks into the prompt
│
├── knowledge_base/                               ⏳ PHASE 4
│   └── (your source docs go here — PDFs, txt, etc.)
│
├── memory/                                       ⏳ PHASE 5
│   ├── __init__.py
│   ├── memory_manager.py      ⏳ session store, get/save/append CRUD
│   ├── summarizer.py           ⏳ async LLM call summarizing old turns
│   └── context_builder.py     ⏳ builds context: raw → last exchange → summaries
│
├── emotion/                                      ⏳ PHASE 6
│   ├── __init__.py
│   ├── emotion_detector.py    ⏳ detects intent/emotion from text
│   └── voice_style_mapper.py  ⏳ maps emotion → ElevenLabs voice settings
│   (call_state_machine.py / websocket_routes.py also get touched here
│    for true mid-stream audio cancellation on barge-in)
│
└── tests/                                        ⏳ PHASE 7
    ├── __init__.py
    ├── test_vad.py
    ├── test_state_machine.py
    ├── test_llm_service.py
    ├── test_memory.py
    ├── test_websocket.py
    └── (+ Dockerfile, deployment config, rate limiting, monitoring)