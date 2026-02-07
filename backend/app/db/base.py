from sqlmodel import Session
from app.db.session import SessionLocal, engine
from app.db.base_class import Base

# Імпорт моделей для Alembic metadata
from app.models.user import User  # noqa
from app.models.currency import CurrencyRate  # noqa
from app.models.product import Product, ProductData  # noqa


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
