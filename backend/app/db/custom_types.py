import base64
from typing import Any, Optional
from sqlalchemy.types import TypeDecorator, String
from pythemis.scell import SCellSeal

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, master_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scell = SCellSeal(key=base64.urlsafe_b64decode(master_key))

    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            encrypted_bytes = self.scell.encrypt(value.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('ascii')
        return value

    def process_result_value(self, value: Any, dialect) -> Optional[str]:
        if value is None:
            return None
        try:
            encrypted_bytes = base64.urlsafe_b64decode(value)
            return self.scell.decrypt(encrypted_bytes).decode('utf-8')
        except Exception:
            return None
