#!/bin/bash
# Auto-kill port 8000 if occupied
lsof -ti:8000 | xargs kill -9 2>/dev/null

cd backend
# Activate venv if it exists, else skip
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Let settings.py handle host/port/reload from .env
python -m app.main
