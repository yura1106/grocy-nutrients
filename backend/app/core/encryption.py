"""
Encryption utilities for sensitive fields using Themis SCellSeal.

Grocy API keys are encrypted per-user using the user's bcrypt password hash
as the symmetric key. This ensures that each user's secrets are tied to their
own credentials and cannot be decrypted without the correct password hash.

Library: pythemis (Themis by Cossack Labs)
Primitive: SCellSeal — authenticated symmetric encryption.
"""

import base64

from pythemis.scell import SCellSeal


def _scell_for_password_hash(password_hash: str) -> SCellSeal:
    """Create a SCellSeal instance keyed by a bcrypt password hash."""
    return SCellSeal(key=password_hash.encode("utf-8"))


def encrypt_api_key(value: str, password_hash: str) -> str:
    """Encrypt a plaintext API key using the user's password hash.

    Returns a base64url-encoded ciphertext suitable for database storage.
    """
    scell = _scell_for_password_hash(password_hash)
    encrypted_bytes = scell.encrypt(value.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted_bytes).decode("ascii")


def decrypt_api_key(value: str, password_hash: str) -> str | None:
    """Decrypt a stored API key using the user's password hash.

    Returns the plaintext key, or None if decryption fails
    (e.g. wrong password hash or corrupted data).
    """
    scell = _scell_for_password_hash(password_hash)
    try:
        encrypted_bytes = base64.urlsafe_b64decode(value)
        return str(scell.decrypt(encrypted_bytes).decode("utf-8"))
    except Exception:
        return None


def reencrypt_user_api_keys(db, user_id: int, old_hash: str, new_hash: str) -> None:
    """Re-encrypt all API keys for a user after a password change.

    Decrypts each key with the old password hash and re-encrypts with the new one.
    Keys that fail to decrypt (already corrupted) are left unchanged.
    """
    from sqlmodel import select

    from app.models.household import HouseholdUser

    memberships = db.exec(
        select(HouseholdUser).where(
            HouseholdUser.user_id == user_id,
            HouseholdUser.grocy_api_key.isnot(None),  # type: ignore[union-attr]
        )
    ).all()

    for m in memberships:
        plaintext = decrypt_api_key(m.grocy_api_key, old_hash)
        if plaintext:
            m.grocy_api_key = encrypt_api_key(plaintext, new_hash)
            db.add(m)
