from sqlalchemy.orm import Session

from app.db.base import Base, engine
from app.models.user import User  # Import all models to ensure they're registered


def init_db() -> None:
    """
    Initialize the database by creating all tables
    """
    # Import all models here to ensure they're registered with SQLAlchemy
    # This is needed for create_all to work properly
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")