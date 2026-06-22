#!/bin/bash
cd backend
# Tooling: uv (dev-protocol §3.1). No manual venv activation.
uv run pytest -v tests/
