import json

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings


class EncryptedJSONSerializer:
    """Django signs this encrypted payload; even pending MFA enrollment stays encrypted."""

    def __init__(self):
        self.cipher = MultiFernet([Fernet(key.encode()) for key in settings.MFA_ENCRYPTION_KEYS])

    def dumps(self, obj):
        return self.cipher.encrypt(json.dumps(obj, separators=(",", ":")).encode())

    def loads(self, data):
        return json.loads(self.cipher.decrypt(data))
