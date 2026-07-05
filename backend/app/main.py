import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from app.core.build_info import log_startup_banner, resolve_version

log_startup_banner()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.router_main import router
from app.core.logging_config import setup_industrial_logging
from app.core.settings import settings
from app.modules.sniffer import start_consumer, stop_consumer
from app.modules.dispatcher import get_dispatcher

setup_industrial_logging()

logger = logging.getLogger(__name__)

# --- Startup warning if API Key is not configured ---
if settings.api_key_value is None:
    logger.warning(
        "FIREWALL_API_KEY is not set — all endpoints are unauthenticated. "
        "Set FIREWALL_API_KEY in .env for production deployments."
    )

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


# --- Lifespan (startup / shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    dispatcher = get_dispatcher()
    dispatcher.start(loop)
    app.state.inference_dispatcher = dispatcher
    start_consumer()
    yield
    stop_consumer()
    dispatcher.stop()


app = FastAPI(
    title="Three-Headed Semantic Firewall",
    version=resolve_version(),
    docs_url=None if settings.api_key_value else "/docs",
    redoc_url=None if settings.api_key_value else "/redoc",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Security Headers Middleware ---
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects defense-in-depth HTTP headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=settings.credentials_allowed,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
