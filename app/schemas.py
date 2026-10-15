from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SignalSide = Literal["BUY", "SELL", "HOLD"]
ChartInterval = Literal["1m", "5m", "15m", "1h", "4h", "1d"]


class Signal(BaseModel):
    """Bentuk data sinyal. Harus selalu sama dengan interface Signal di
    frontend (src/types/signals.ts). Nama field di JSON memakai camelCase."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    symbol: str
    side: SignalSide
    # Tingkat keyakinan model, 0 sampai 100.
    confidence: float = Field(ge=0, le=100)
    timeframe: ChartInterval
    reason: str
    # Waktu sinyal dibuat, dalam milidetik sejak epoch (sama seperti Date.now()).
    created_at: int