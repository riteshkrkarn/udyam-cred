"""Documents endpoints: file upload and management."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Document
from app.schemas import DocumentOut
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["documents"])

UPLOAD_DIR = Path("data/documents")
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".xls", ".xlsx"}


@router.post("/{application_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    application_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentOut:
    """
    Upload document (multipart file + doc_type).

    Saves to data/documents/{app_id}/{doc_type}/filename.
    Validates file type (pdf, jpg, png, xlsx).
    Creates Document record.
    """
    # Check application exists
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Validate doc_type
    valid_types = {"bill", "purchase", "ledger", "statement", "other"}
    if doc_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {doc_type}")

    # Validate file extension
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {file_ext}"
        )

    # Create upload directory
    app_dir = UPLOAD_DIR / str(application_id) / doc_type
    app_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = app_dir / (file.filename or "document")
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create Document record
    document = Document(
        application_id=application_id,
        document_type=doc_type,
        file_path=str(file_path),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return DocumentOut(
        id=document.id,
        application_id=document.application_id,
        document_type=document.document_type,
        file_path=document.file_path,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@router.get("/{application_id}/documents")
def list_documents(
    application_id: int,
    db: Session = Depends(get_db),
) -> list[DocumentOut]:
    """List documents for application."""
    application = db.query(Application).filter_by(id=application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    documents = db.query(Document).filter_by(application_id=application_id).all()

    return [
        DocumentOut(
            id=doc.id,
            application_id=doc.application_id,
            document_type=doc.document_type,
            file_path=doc.file_path,
            uploaded_at=doc.uploaded_at.isoformat(),
        )
        for doc in documents
    ]
