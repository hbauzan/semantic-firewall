#!/bin/bash
cd backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
pytest -v perform_tests.py
