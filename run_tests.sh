#!/bin/bash
cd backend
# Tooling: uv. No manual venv activation.
uv run pytest -v tests/
