# Claude Suggest

A Python Flask web server that serves a single HTML interface and exposes a `/api/suggest` endpoint that forwards POST requests to the Anthropic Claude API.

## Run & Operate

- `cd flask-app && python app.py` — run the Flask server (port 5000)
- Workflow: **Flask App** — starts automatically

## Stack

- Python 3.11 + Flask 3
- Anthropic Python SDK
- Required env: `ANTHROPIC_API_KEY` — your Anthropic API key (set in Secrets)

## Where things live

- `flask-app/app.py` — Flask server (serves HTML + `/api/suggest` endpoint)
- `flask-app/templates/index.html` — single-page HTML UI
- `flask-app/requirements.txt` — Python dependencies

## API

### `POST /api/suggest`

Accepts JSON. Two calling styles:

**Simple prompt:**
```json
{ "prompt": "Your question here" }
```

**Full messages array:**
```json
{
  "messages": [{"role": "user", "content": "..."}],
  "system": "Optional system prompt",
  "model": "claude-sonnet-4-6",
  "max_tokens": 8192
}
```

**Response:**
```json
{
  "suggestion": "...",
  "model": "claude-sonnet-4-6",
  "stop_reason": "end_turn",
  "usage": { "input_tokens": 13, "output_tokens": 42 }
}
```

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._
