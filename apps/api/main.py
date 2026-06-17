"""
Crypto Radar v7.0 — FastAPI backend.

Jalan bersama Discord bot di 1 Docker container (Discord bot di-start via
lifespan hook, bukan proses terpisah).

Endpoints:
    GET  /                  — health root (public)
    GET  /health            — health JSON (public)
    GET  /api/v1/strategies — list strategi yang aktif (public)
    POST /api/v1/scan       — trigger scan manual (auth: API_INTERNAL_TOKEN)
    GET  /api/v1/signals    — recent signals (public, placeholder)
    WS   /ws/signals        — live signals via WebSocket (public, placeholder)
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Tambahkan root project ke sys.path supaya `import radar` & `import main` jalan
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Security, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import radar  # noqa: E402
from strategies import STRATEGY_REGISTRY  # noqa: E402

# ══════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════
_APP_START_TIME = time.time()


# ══════════════════════════════════════════════
# CORS — Vercel domain + localhost untuk dev
# ══════════════════════════════════════════════
def _get_cors_origins() -> list[str]:
    raw = os.environ.get("API_CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# ══════════════════════════════════════════════
# LIFESPAN — startup & shutdown hooks
# ══════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP ===
    discord_token = os.environ.get("DISCORD_TOKEN", "")
    if discord_token:
        try:
            import main as discord_main

            async def _run_discord() -> None:
                try:
                    await discord_main.bot.start(discord_token)
                except Exception as e:  # noqa: BLE001
                    print(f"❌ Discord bot failed: {e}")

            asyncio.create_task(_run_discord())
            print("🤖 Discord bot started in background task")
        except Exception as e:  # noqa: BLE001
            print(f"⚠️  Could not start Discord bot: {e}")
    else:
        print("ℹ️  DISCORD_TOKEN not set — running API-only mode")

    yield

    # === SHUTDOWN ===
    try:
        import main as discord_main
        await discord_main.bot.close()
    except Exception:  # noqa: BLE001
        pass


# ══════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════
app = FastAPI(
    title="Crypto Radar API",
    version="7.0.0",
    description="Multi-strategy crypto sniper API for Discord + Web dashboard",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════
def _verify_internal_token(x_internal_token: str | None = None) -> str:
    """Verifikasi API_INTERNAL_TOKEN. Return token kalau valid, raise 401 kalau tidak."""
    expected = os.environ.get("API_INTERNAL_TOKEN", "")
    if not expected:
        return "dev-mode"
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")
    return x_internal_token


# ══════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════
class StrategyInfo(BaseModel):
    name: str
    direction: str
    risk_reward_ratio: float
    stop_loss_pct: float
    lookback: dict[str, int]


class ScanRequest(BaseModel):
    scan_limit: int | None = None
    strategies: list[str] | None = None


class ScanResponse(BaseModel):
    status: str
    signals_found: int
    coins_scanned: int
    strategies_run: list[str]


# ══════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════
@app.get("/")
async def root():
    return {"name": "Crypto Radar API", "version": "7.0.0", "status": "ok"}


@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "version": "7.0.0",
        "uptime_seconds": time.time() - _APP_START_TIME,
        "active_strategies": list(STRATEGY_REGISTRY.keys()),
        "sinks_registered": len(radar._signal_sinks),
        "scan_limit": radar.SCAN_LIMIT,
        "vol_spike_threshold": radar.VOL_SPIKE_THRESHOLD,
    })


@app.get("/api/v1/strategies", response_model=list[StrategyInfo])
async def list_strategies():
    """List semua strategi yang terdaftar beserta konfigurasinya."""
    result = []
    for _name, cls in STRATEGY_REGISTRY.items():
        instance = cls()
        result.append(StrategyInfo(
            name=instance.name,
            direction=instance.direction,
            risk_reward_ratio=instance.risk_reward_ratio,
            stop_loss_pct=instance.stop_loss_pct,
            lookback=instance.required_lookback(),
        ))
    return result


@app.post("/api/v1/scan", response_model=ScanResponse)
async def trigger_scan(
    req: ScanRequest,
    _token: str = Security(_verify_internal_token, scopes=["internal"]),
):
    """
    Trigger scan manual. Butuh header `X-Internal-Token: <token>`.
    Jalankan di background thread karena radar.run_scanner() blocking.
    """
    if req.scan_limit:
        radar.SCAN_LIMIT = req.scan_limit
    if req.strategies:
        os.environ["STRATEGIES"] = ",".join(req.strategies)

    try:
        await asyncio.to_thread(radar.run_scanner)
        return ScanResponse(
            status="completed",
            signals_found=-1,
            coins_scanned=radar.SCAN_LIMIT,
            strategies_run=list(STRATEGY_REGISTRY.keys()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}") from e


@app.get("/api/v1/signals")
async def list_signals(limit: int = 50):
    """Recent signals. Placeholder — nantinya baca dari Supabase."""
    return {
        "status": "not_implemented",
        "message": "Will be wired to Supabase in Phase 1",
        "limit": limit,
    }


# ══════════════════════════════════════════════
# WEBSOCKET — live signals (placeholder untuk Phase 1)
# ══════════════════════════════════════════════
@app.websocket("/ws/signals")
async def ws_signals(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "connected", "message": "Live signals stream (placeholder)"})
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
    )
