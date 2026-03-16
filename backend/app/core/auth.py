from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.encryption import decrypt_api_key
from app.db.base import get_db
from app.models.household import Household, HouseholdUser
from app.models.user import User
from app.schemas.user import TokenPayload
from app.services.grocy_api import GrocyAPI

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current user based on the JWT token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # Only accept access tokens for authentication
        if token_data.purpose and token_data.purpose != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    statement = select(User).where(User.id == token_data.sub)
    user = db.exec(statement).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


def get_grocy_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    household_id: int = Query(...),
) -> GrocyAPI:
    """
    FastAPI dependency that returns a configured GrocyAPI instance
    using credentials from the user's household membership.

    Requires household_id query parameter. Looks up:
    - grocy_api_key from HouseholdUser (per-user, per-household)
    - grocy_url from Household
    """
    hu = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.household_id == household_id,
            HouseholdUser.user_id == current_user.id,
            HouseholdUser.is_active == True,  # noqa: E712
        )
    ).first()
    if not hu:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this household.",
        )
    if not hu.grocy_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grocy API key not configured for this household. Please set it in household settings.",
        )
    plaintext_key = decrypt_api_key(hu.grocy_api_key, current_user.hashed_password)
    if not plaintext_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt Grocy API key. Please re-save your key in household settings.",
        )
    household = db.exec(select(Household).where(Household.id == household_id)).first()
    if not household or not household.grocy_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grocy URL not configured for this household.",
        )
    return GrocyAPI(key=plaintext_key, url=household.grocy_url)
