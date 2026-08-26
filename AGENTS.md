# Deep Research Agent — REX Recursive Exploration Explorer

## Development Setup

| Command | Description |
|---|---|
| `backend\start_servers.bat` | Starts both backend (port 8000) and frontend (port 3000) |
| `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000` | Start the FastAPI backend |
| `cd frontend && npm run dev` | Start Next.js dev server (port 3000) |

## Backend (FastAPI)

- **Entrypoint**: `backend/main.py` — FastAPI app, port 8000
- **LLM requirement**: Ollama must be running at `localhost:11434` for LLM calls
- **Default models**: `PLANNER_MODEL=phi3:mini`, `REPORT_MODEL=qwen2.5:3b`
- **Cache**: Redis preferred (port 6379), falls back to file-based `backend_cache.json`
- **Env vars**: read from `backend/.env`; see `_check_env.py` for required vars
- **Quality check**: Run `python _check_quality.py` against running backend at http://localhost:8000

## Frontend (Next.js)

- **Entrypoint**: `frontend/` — Next.js 16.2.9, port 3000
- **Scripts**: `npm run dev` (dev), `npm run build`, `npm run lint` (eslint)
- **Tailwind CSS v4**: config in `frontend/tailwind.config.mjs` (if present)
- **Breaking note**: Frontend AGENTS.md warns this is "NOT the Next.js you know" — breaking changes in APIs/conventions. Check `node_modules/next/dist/docs/` for deprecations.

## Research Pipeline Quirks

- Sub-question generation uses topic-aware templates (stable_technical/emerging_trend/company_product/etc.)
- LLM calls go through Ollama; `_ollama_available()` checks model availability before calling
- Report quality checks (via `_check_quality.py`): verify no boilerplate, no disclaimers, no duplicate paragraphs, no query repetition in sub-questions
- n8n integration: `/api/n8n/health` and `/api/n8n/batch-research` endpoints
- Web scraping uses Playwright (headless Chromium) with boilerplate filtering

## Testing

- Quality checks: `python _check_quality.py` (requires backend running at localhost:8000)
- E2E tests: `test_e2e.py`, `test_e2e_full.py` in root
- Backend tests: numerous `test_*.py` files in `backend/`
- No CI workflows configured in this repo