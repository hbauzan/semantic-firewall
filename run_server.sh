#!/bin/bash
# Auto-kill port 8000 if occupied
lsof -ti:8000 | xargs kill -9 2>/dev/null

cd backend
# Tooling: uv. No manual venv activation.
# Let settings.py handle host/port/reload from .env
uv run python -m app.main
