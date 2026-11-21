"""Photo endpoints: upload, list, and verify photos."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Photo, User
from app.schemas import PhotoOut, PhotoUploadInput
from app.utils import utcnow_naive

router = APIRouter(prefix="/api/applications", tags=["photos"])


@router.post(
    "/{application_id}/photos",
    response_model=PhotoOut,
    status_code=201,
)
def upload_photo(
    application_id: int,
    photo: PhotoUploadInput,
    db: Session = Depends(get_db),
) -> PhotoOut:
    """
    Upload a geo-tagged photo for an application.

    Photo types: shop_front | shelves | bills | rent_receipt | udyam | gst
    """
    # Check if application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create photo record
    db_photo = Photo(
        application_id=application_id,
        photo_type=photo.photo_type,
        photo_path=photo.photo_path,
        location_lat=photo.location_lat,
        location_lng=photo.location_lng,
        random_code_written=photo.random_code_written,
        verification_status="pending",
        created_at=utcnow_naive(),
    )
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)

    return PhotoOut(
        id=db_photo.id,
        application_id=db_photo.application_id,
        photo_type=db_photo.photo_type,
        photo_path=db_photo.photo_path,
        location_lat=db_photo.location_lat,
        location_lng=db_photo.location_lng,
        verification_status=db_photo.verification_status,
        verified_at=db_photo.verified_at.isoformat() if db_photo.verified_at else None,
    )


@router.get("/{application_id}/photos", response_model=list[PhotoOut])
def list_photos(
    application_id: int,
    db: Session = Depends(get_db),
) -> list[PhotoOut]:
    """
    List all photos for an application.
    """
    # Check if application exists
    app = (
        db.query(Application)
        .filter(Application.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    photos = (
        db.query(Photo)
        .filter(Photo.application_id == application_id)
        .all()
    )

    return [
        PhotoOut(
            id=p.id,
            application_id=p.application_id,
            photo_type=p.photo_type,
            photo_path=p.photo_path,
            location_lat=p.location_lat,
            location_lng=p.location_lng,
            verification_status=p.verification_status,
            verified_at=p.verified_at.isoformat() if p.verified_at else None,
        )
        for p in photos
    ]


@router.get("/{application_id}/photos/{photo_id}", response_model=PhotoOut)
def get_photo_details(
    application_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
) -> PhotoOut:
    """
    Get photo details with verification status.
    """
    photo = (
        db.query(Photo)
        .filter(Photo.application_id == application_id, Photo.id == photo_id)
        .first()
    )
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return PhotoOut(
        id=photo.id,
        application_id=photo.application_id,
        photo_type=photo.photo_type,
        photo_path=photo.photo_path,
        location_lat=photo.location_lat,
        location_lng=photo.location_lng,
        verification_status=photo.verification_status,
        verified_at=photo.verified_at.isoformat() if photo.verified_at else None,
    )
