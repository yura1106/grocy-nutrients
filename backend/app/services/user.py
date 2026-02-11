from typing import Optional

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_by_email(db: Session, email: str) -> Optional[User]:
    statement = select(User).where(User.email == email)
    return db.exec(statement).first()


def get_by_username(db: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return db.exec(statement).first()


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    statement = select(User).where(User.id == user_id)
    return db.exec(statement).first()


def create(db: Session, user_in: UserCreate) -> User:
    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update(db: Session, db_user: User, user_in: UserUpdate) -> User:
    # Pydantic v2: model_dump instead of dict
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data["password"])
        del update_data["password"]

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = get_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
