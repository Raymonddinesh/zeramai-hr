from app.deps import SENSITIVE_IDENTITY_DOCUMENT_TYPES, can_access_sensitive_documents
from app.models import Document, User, UserRole


def can_access_person(user: User, person_id: str) -> bool:
    """Determine if a user can access a Person record.
    SUPER_ADMIN and HR_ADMIN have full access. Employees can access their own record.
    """
    if user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN):
        return True
    return bool(user.person_id and str(user.person_id) == str(person_id))


def can_access_document(user: User, doc: Document) -> bool:
    """Object‑level document access.
    * Admin roles have unrestricted access.
    * Sensitive identity documents require special role permission.
    * Regular employees can only access their own non‑sensitive documents.
    """
    if user.role in (UserRole.SUPER_ADMIN, UserRole.HR_ADMIN):
        return True
    if str(doc.document_type) in SENSITIVE_IDENTITY_DOCUMENT_TYPES:
        return can_access_sensitive_documents(user.role)  # type: ignore[arg-type]
    # Non‑sensitive: owner only
    return bool(user.person_id and doc.person_id and str(user.person_id) == str(doc.person_id))
