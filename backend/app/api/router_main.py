"""Main API Router -- entry point that aggregates all endpoint sub-routers.

Replaces the monolithic routes.py (Finding A1 -- Router Decomposition).
Imported by app/main.py via: from app.api.router_main import router
"""
from fastapi import APIRouter
from app.api.endpoints import chat, corpus, config, system

router = APIRouter()

# Chat router must be included without prefix to allow /v1/chat/completions to resolve correctly
router.include_router(chat.router, tags=["Inference"])
router.include_router(corpus.router, tags=["Knowledge"])
router.include_router(config.router, tags=["Configuration"])
router.include_router(system.router, tags=["System"])
