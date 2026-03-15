from datetime import datetime

from sqlmodel import SQLModel


class CurrencyRateBase(SQLModel):
    """Shared currency rate properties"""

    base_currency: str
    target_currency: str
    rate: float


class CurrencyRateCreate(CurrencyRateBase):
    """Properties required to create a currency rate"""

    timestamp: datetime | None = None


class CurrencyRateRead(CurrencyRateBase):
    """Properties returned to client"""

    id: int
    timestamp: datetime

    model_config = {"from_attributes": True}
