import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import Signal
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/signals", response_model=list[Signal], response_model_by_alias=True)
def list_signals() -> list[Signal]:
    return get_signals()