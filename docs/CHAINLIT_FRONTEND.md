# Chainlit Frontend (Text + Voice)

This project now includes a separate Chainlit UI entrypoint at:

- `frontend/chainlit_app.py`

It connects to the same LangGraph + MCP backend flow that `main.py` uses, but through a web chat interface.

## What it supports

- Text chat input
- Voice input from browser audio stream (if Chainlit audio hooks are available)
- Voice input fallback via audio file upload command: `/voice`

## Install

```bash
pip install -r requirements.txt
```

## Run

From the repository root:

```bash
chainlit run frontend/chainlit_app.py -w
```

Then open the URL shown by Chainlit (usually `http://localhost:8000`).

## Notes

- The frontend creates a unique thread ID per Chainlit session.
- It reuses your existing graph and tool routing logic without changing `main.py`.
- If browser microphone capture is not available in your Chainlit version/environment, use `/voice` and upload an audio file.
