# Findora Portable

Offline-first lost-and-found tracker with local SQLite storage, explainable match scoring, and optional local AI (llama.cpp + Qwen GGUF).

## Requirements
- Windows 10/11 x64
- 12+ GB RAM recommended (16 GB is marginal for Qwen 7B Q5)
- Internet for first-time SETUP; no Internet required after runtime/model downloads

## Setup and run
1. Extract the ZIP.
2. Run `SETUP.bat` to download embedded Python, llama.cpp runtime, and Qwen model.
3. Run `START.bat`. It opens the dashboard at `http://127.0.0.1:8765`.
4. To move offline, copy the entire folder to your USB drive. Keep `runtime`, `models`, `data`, and `logs`.

## Privacy
The server binds to localhost only. Lost/found reports remain in `data/findora.db`. AI requests are sent only to the local model server at `127.0.0.1:8081`.

## Matching
Same category required. Color/brand/location partial matches, description similarity, and date proximity contribute to a score. Reports more than 30 days apart are rejected. Potential match threshold: 45.

## Troubleshooting
- Setup is resumable for downloads (`curl -C -`). It checks the response size where headers are available and enforces a minimum model size.
- If llama-server is not present, report creation/search/matching still works; AI chat returns offline fallback guidance.
- Local AI can be slow or fail to load on a 16 GB system with Q5 7B weights. Close other applications and use the AI model on a higher-RAM machine if necessary.
