"""Pure httpx REST client for Three-Headed Semantic Firewall backend API.

No internal Python backend imports; communicates strictly via HTTP REST.
"""
import logging
from typing import Any
import httpx

from rompepepe.state.models import TelemetryTrace, TelemetryTraceItem

logger = logging.getLogger(__name__)


class FirewallClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=self.timeout)

    async def get_health(self) -> dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.get("/health")
            resp.raise_for_status()
            return resp.json()

    async def get_config(self) -> dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.get("/galaxy/config")
            resp.raise_for_status()
            data = resp.json()
            return data.get("config", data)

    async def update_config(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.post("/galaxy/config", json=config_dict)
            resp.raise_for_status()
            data = resp.json()
            return data.get("config", data)

    async def get_packs(self) -> list[dict[str, Any]]:
        async with self._get_client() as client:
            resp = await client.get("/corpus/packs")
            resp.raise_for_status()
            data = resp.json()
            return data.get("packs", [])

    async def audit(self, query: str) -> TelemetryTrace:
        async with self._get_client() as client:
            resp = await client.post("/audit", json={"query": query})
            resp.raise_for_status()
            data = resp.json()
            
            trace_items: list[TelemetryTraceItem] = []
            cosine_val: float | None = None
            exc_val: float | None = None
            noise_val: float | None = None

            raw_trace = data.get("trace", [])
            if isinstance(raw_trace, list):
                for item in raw_trace:
                    if isinstance(item, dict):
                        flt = item.get("filter", "unknown")
                        score = float(item.get("score", 0.0))
                        thresh = float(item.get("threshold", 0.0))
                        passed = bool(item.get("passed", True))
                        order = int(item.get("order", 0))
                        
                        if flt == "cosine":
                            cosine_val = score
                        elif flt == "excitation":
                            exc_val = score
                        elif flt in ("noise", "entropy"):
                            noise_val = score

                        trace_items.append(
                            TelemetryTraceItem(
                                filter=flt,
                                order=order,
                                score=score,
                                threshold=thresh,
                                passed=passed,
                                details=item.get("details", {}),
                            )
                        )

            return TelemetryTrace(
                passed=bool(data.get("passed", True)),
                breach_reason=data.get("breach_reason"),
                trace=trace_items,
                activations=int(data.get("activations", 0)),
                text=str(data.get("text", "")),
                cosine_delta=cosine_val,
                excitation_level=exc_val,
                noise_entropy=noise_val,
            )

    async def chat(self, prompt: str) -> dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.post("/chat", json={"prompt": prompt})
            resp.raise_for_status()
            return resp.json()

    async def get_profiles(self) -> list[str]:
        async with self._get_client() as client:
            resp = await client.get("/galaxy/profiles")
            resp.raise_for_status()
            data = resp.json()
            return data.get("profiles", [])

    async def load_profile(self, name: str) -> dict[str, Any]:
        async with self._get_client() as client:
            resp = await client.post(f"/galaxy/profiles/load/{name}")
            resp.raise_for_status()
            return resp.json()
