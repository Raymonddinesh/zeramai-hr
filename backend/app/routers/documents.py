import io
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    get_current_user,
    has_permission,
    log_audit,
)
from app.deps.authorization import can_access_document
from app.models import AuditResult, Document, DocumentStatus, User
from app.storage import build_storage_key, get_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}



@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    person_id: str = Form(...),
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Permission validation
    if has_permission(current_user, "documents:upload", db):
        pass  # admin or HR can upload any document
    elif has_permission(current_user, "documents:upload_own", db) and person_id == current_user.person_id:
        pass  # employee can upload own document
    else:
        log_audit(db, user=current_user, action="document_upload", entity="document",
                  entity_id=None, result=AuditResult.DENIED, request=request,
                  metadata={"person_id": person_id, "document_type": document_type})
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions to upload this document")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File exceeds 10MB limit")

    key = build_storage_key(person_id, document_type, file.filename)
    get_storage().put_object(key, data)

    doc = Document(
        person_id=person_id,
        document_type=document_type,
        file_name=file.filename,
        storage_key=key,
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=current_user.id,
        upload_date=datetime.utcnow(),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit(db, user=current_user, action="document_uploaded", entity="document",
              entity_id=doc.id, result=AuditResult.SUCCESS, request=request,
              metadata={"document_type": document_type})
    return {"id": doc.id, "status": doc.status.value}


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Backend-proxied streaming (Approach B). No presigned URL is ever issued:
    authorization is checked on THIS request, and the audit log entry
    reflects a real download, not a URL-mint event.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    # Permission validation
    if has_permission(current_user, "documents:download", db) or has_permission(current_user, "documents:download_own", db) and doc.person_id == current_user.person_id:
        allowed = True
    else:
        allowed = False

    if not allowed or not can_access_document(current_user, doc):
        log_audit(db, user=current_user, action="document_download", entity="document",
                  entity_id=document_id, result=AuditResult.DENIED, request=request)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to access this document")

    try:
        data = get_storage().get_object_bytes(doc.storage_key)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stored file missing")

    log_audit(db, user=current_user, action="document_download", entity="document",
              entity_id=document_id, result=AuditResult.SUCCESS, request=request)

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'},
    )
