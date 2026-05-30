"""Main API Router -- entry point that aggregates all endpoint sub-routers.

Replaces the monolithic routes.py (Finding A1 -- Router Decomposition).
Imported by app/main.py via: from app.api.router_main import router
"""
from fastapi import APIRouter
from app.api.endpoints import corpus, config, chat, system

router = APIRouter()
router.include_router(corpus.router)
router.include_router(config.router)
router.include_router(chat.router)
router.include_router(system.router)
