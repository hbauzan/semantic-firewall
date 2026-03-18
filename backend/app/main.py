import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(title="Phase-Lock Semantic Firewall", version="2.10.0")

# --- CORS: env-driven, secure defaults ---
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
# allow_credentials=True is only safe with explicit origins, never with "*"
_use_credentials = "*" not in _allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=_use_credentials,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "true").lower() == "true"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
