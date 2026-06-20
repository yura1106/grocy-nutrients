from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # The household this key grants MCP access to; caller must be an active member.
    household_id: int


class APIKeyRead(BaseModel):
    """API key metadata — never includes the secret."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    key_prefix: str
    # None for legacy keys minted before the per-key household binding.
    household_id: int | None = None
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    expires_at: datetime | None = None


class APIKeyCreateResponse(APIKeyRead):
    """Returned once at creation — carries the plaintext key (shown only here)."""

    key: str
