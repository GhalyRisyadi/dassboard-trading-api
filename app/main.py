import os
from collections.abc import AsyncIterator

import httpx2 as httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import Signal
from app.services.market_data import MarketDataUnavailable
from app.services.signals import get_signals

# Alamat frontend yang boleh memanggil API ini. Bisa diganti lewat variabel
# lingkungan CORS_ORIGINS, dipisah koma.
DEFAULT_ORIGINS = "http://localhost:5173"
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]

app = FastAPI(title="Dashboard Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=10) as client:
        yield client


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/signals", response_model=list[Signal], response_model_by_alias=True)
async def list_signals(client: httpx.AsyncClient = Depends(get_http_client)) -> list[Signal]:
    try:
        return await get_signals(client)
    except MarketDataUnavailable as error:
        raise HTTPException(status_code=502, detail=str(error)) from error