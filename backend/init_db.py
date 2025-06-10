from sqlalchemy import create_engine
from app.db.base import Base
from app.core.config import settings

def init_db():
    engine = create_engine(str(settings.DATABASE_URL))
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db() 