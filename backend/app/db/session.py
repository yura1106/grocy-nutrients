from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from app.core.config import settings

# Convert the URL to string to make it compatible with SQLAlchemy
engine = create_engine(str(settings.DATABASE_URL))

# Use SQLModel Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)
