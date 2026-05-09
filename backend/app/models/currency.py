from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class CurrencyRate(SQLModel, table=True):
    """
    CurrencyRate model - stores currency exchange rates
    """

    __tablename__ = "currency_rates"

    id: int | None = Field(default=None, primary_key=True, index=True)
    base_currency: str = Field(index=True)
    target_currency: str = Field(index=True)
    rate: float
    timestamp: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
