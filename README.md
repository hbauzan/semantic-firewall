# Phase-Lock Semantic Firewall (Distilled Core)

A highly optimized RAG-enabled local LLM client utilizing the Dimensional Excitation Math theorem to validate geometric semantic boundaries around sensitive vectors. 

## Requirements
- Python 3.10+
- Node.js 20+
- `ollama` with `llama3.1` model pulled and running (`ollama run llama3.1`)

## Execution Instructions
We provide a DOS-style TUI to orchestrate the infrastructure smoothly. From the root directory:

```bash
chmod +x ./run_commander.sh
./run_commander.sh
```

### Menu Options
1. **[S] Start Server**: Activates the virtual python environment and boots FastAPI via `uvicorn`.
2. **[U] Start UI**: Starts the React 19 Frontend Vite server.
3. **[T] Run Tests**: Triggers the Pytest verification pipeline assessing logic.
4. **[O] Ollama Menu**: Instantiates local terminal chat with the raw model directly.

## Telemetry HUD & Control Panel
Access the UI via `http://localhost:5173`. 
Adjust `Excitation Threshold` (0-1024) and `Noise Tolerance` dynamically.
Initiate chat queries prefaced with `[FW=ON]` to enforce firewall policies dynamically against the LanceDB local context array.
