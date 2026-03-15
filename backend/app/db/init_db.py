from sqlalchemy import create_engine

from app.core.config import settings
from app.db.base import Base


def init_db():
    engine = create_engine(str(settings.DATABASE_URL))
    Base.metadata.create_all(bind=engine, checkfirst=True)
