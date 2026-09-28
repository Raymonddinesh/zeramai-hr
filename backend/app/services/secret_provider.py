"""
SecretProvider service - Module 14: Enterprise IAM & Integration Hub.

Secure secret management abstraction. Encrypts sensitive values (client secrets,
bearer tokens, webhook signing keys, etc.) using Fernet symmetric encryption
derived from application configuration. Secrets are stored in `encrypted_secrets`
and referenced via opaque UUIDs (`secret_reference`). Raw plaintext secrets are
never persisted directly to database tables or exposed in API responses.
"""
import base64
import hashlib
from typing import Optional
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.models_integrations import EncryptedSecret


class SecretProvider:
    @staticmethod
    def _get_fernet() -> Fernet:
        # Derive 32-byte url-safe base64 key from settings.jwt_secret
        digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)

    @classmethod
    def store_secret(
        cls,
        db: Session,
        tenant_id: str,
        secret_type: str,
        plaintext: str,
        description: Optional[str] = None,
    ) -> str:
        """Encrypts plaintext and stores it in EncryptedSecret. Returns secret_reference (id)."""
        f = cls._get_fernet()
        ciphertext = f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        
        record = EncryptedSecret(
            tenant_id=tenant_id,
            secret_type=secret_type,
            ciphertext=ciphertext,
            key_version=1,
            description=description,
        )
        db.add(record)
        db.flush()
        return record.id

    @classmethod
    def get_secret(
        cls,
        db: Session,
        tenant_id: str,
        secret_reference: str,
    ) -> Optional[str]:
        """Retrieves and decrypts secret for given tenant and secret_reference."""
        if not secret_reference:
            return None
        query = db.query(EncryptedSecret).filter(
            EncryptedSecret.id == secret_reference,
            EncryptedSecret.tenant_id == tenant_id,
        )
        record = query.first()
        if not record:
            return None
        
        f = cls._get_fernet()
        try:
            decrypted = f.decrypt(record.ciphertext.encode("utf-8")).decode("utf-8")
            return decrypted
        except InvalidToken:
            return None

    @classmethod
    def update_secret(
        cls,
        db: Session,
        tenant_id: str,
        secret_reference: str,
        new_plaintext: str,
    ) -> bool:
        """Rotates/updates an existing secret reference with new plaintext."""
        record = db.query(EncryptedSecret).filter(
            EncryptedSecret.id == secret_reference,
            EncryptedSecret.tenant_id == tenant_id,
        ).first()
        if not record:
            return False
        
        f = cls._get_fernet()
        record.ciphertext = f.encrypt(new_plaintext.encode("utf-8")).decode("utf-8")
        record.key_version += 1
        db.flush()
        return True

    @classmethod
    def delete_secret(
        cls,
        db: Session,
        tenant_id: str,
        secret_reference: str,
    ) -> bool:
        """Deletes an encrypted secret record."""
        record = db.query(EncryptedSecret).filter(
            EncryptedSecret.id == secret_reference,
            EncryptedSecret.tenant_id == tenant_id,
        ).first()
        if not record:
            return False
        db.delete(record)
        db.flush()
        return True
