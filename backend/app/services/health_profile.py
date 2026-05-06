from sqlmodel import Session, select

from app.core.auth import AuthenticatedUser
from app.models.user_health_profile import UserHealthProfile
from app.schemas.user import HealthParametersRead, HealthParametersUpdate


def get_health_params(db: Session, user: AuthenticatedUser) -> HealthParametersRead:
    profile = db.exec(
        select(UserHealthProfile).where(UserHealthProfile.user_id == user.id)
    ).first()

    data: dict = {"gender": user.gender, "date_of_birth": user.date_of_birth}
    if profile:
        data.update(profile.model_dump(exclude={"id", "user_id", "updated_at"}))

    return HealthParametersRead(**data)


def update_health_params(
    db: Session, user: AuthenticatedUser, params_in: HealthParametersUpdate
) -> HealthParametersRead:
    update_data = params_in.model_dump(exclude_unset=True)

    # Split: gender + date_of_birth → User, rest → UserHealthProfile
    user_fields: dict = {}
    for k in ("gender", "date_of_birth"):
        if k in update_data:
            user_fields[k] = update_data.pop(k)

    if user_fields:
        for field, value in user_fields.items():
            setattr(user, field, value)
        db.add(user)

    if update_data:
        profile = db.exec(
            select(UserHealthProfile).where(UserHealthProfile.user_id == user.id)
        ).first()
        if not profile:
            profile = UserHealthProfile(user_id=user.id)
            db.add(profile)
        for field, value in update_data.items():
            setattr(profile, field, value)

    db.commit()
    db.refresh(user)
    return get_health_params(db, user)
