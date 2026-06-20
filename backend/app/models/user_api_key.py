from datetime import datetime

from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, SQLModel


class UserAPIKey(SQLModel, table=True):
    """Long-lived API key for non-browser clients (e.g. the MCP server).

    Plaintext `gnk_<key_prefix>_<secret>`; only prefix + sha256(secret) stored.
    """

    __tablename__ = "user_api_keys"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    # Household this key is scoped to. NULL for legacy keys minted before the
    # per-key binding — MCP auth rejects NULL, so those keys must be re-minted.
    household_id: int | None = Field(
        default=None, foreign_key="households.id", index=True, nullable=True
    )
    name: str = Field(nullable=False)
    key_prefix: str = Field(index=True, nullable=False)
    key_hash: str = Field(nullable=False)
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    last_used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    expires_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
