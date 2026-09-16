"""
Private document storage abstraction.

Deliberate design choice (see architecture review): NO presigned URLs are
generated and handed to the browser. Every read goes through
`get_object_bytes`, called only from a route that has already re-checked
authorization for *this specific request*. The storage backend (local disk
in dev, S3/Azure Blob in production) is never given public or direct-access
permissions — the app is the only thing that can reach it.

Swap `LocalDiskStorage` for an S3 implementation in production by
implementing the same three methods; nothing above this layer should need
to change.
"""

import os
import uuid
from abc import ABC, abstractmethod

from app.config import settings


class StorageBackend(ABC):
    @abstractmethod
    def put_object(self, key: str, data: bytes) -> None: ...

    @abstractmethod
    def get_object_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def delete_object(self, key: str) -> None: ...


class LocalDiskStorage(StorageBackend):
    """Development-only backend. Production must use an S3-compatible /
    Azure Blob backend with bucket-level public access disabled."""

    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _resolve(self, key: str) -> str:
        # Reject any key that tries to escape base_path (path traversal).
        full = os.path.realpath(os.path.join(self.base_path, key))
        if not full.startswith(os.path.realpath(self.base_path)):
            raise ValueError("Invalid storage key")
        return full

    def put_object(self, key: str, data: bytes) -> None:
        full = self._resolve(key)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)

    def get_object_bytes(self, key: str) -> bytes:
        with open(self._resolve(key), "rb") as f:
            return f.read()

    def delete_object(self, key: str) -> None:
        full = self._resolve(key)
        if os.path.exists(full):
            os.remove(full)


def build_storage_key(person_id: str, document_type: str, original_filename: str) -> str:
    """Opaque, non-guessable key. Never derived purely from person_id +
    document_type, so even if a key leaked, it isn't enumerable."""
    ext = os.path.splitext(original_filename)[1]
    return f"{person_id}/{document_type}/{uuid.uuid4().hex}{ext}"


def get_storage() -> StorageBackend:
    if settings.storage_provider == "local":
        return LocalDiskStorage(settings.storage_local_path)
    raise NotImplementedError(
        f"Storage provider '{settings.storage_provider}' not yet implemented — "
        "add an S3/Azure Blob backend here for production."
    )
