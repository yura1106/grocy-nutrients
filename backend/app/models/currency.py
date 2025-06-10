from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.base_class import Base
from datetime import datetime

class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True, index=True)
    base_currency = Column(String, index=True)
    target_currency = Column(String, index=True)
    rate = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

    class Config:
        orm_mode = True 