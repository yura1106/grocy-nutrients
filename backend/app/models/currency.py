from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class CurrencyRate(SQLModel, table=True):
    """
    CurrencyRate model - stores currency exchange rates
    """
    __tablename__ = "currency_rates"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    base_currency: str = Field(index=True)
    target_currency: str = Field(index=True)
    rate: float
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
