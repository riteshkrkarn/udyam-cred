"""Challenge service endpoints for photo anti-staging validation."""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Challenge, User
from app.schemas import ChallengeOut, ChallengeRequest
from app.utils import utcnow_naive

router = APIRouter(prefix="/applications", tags=["challenges"])


def generate_challenge_code(length: int = 4) -> str:
    """Generate a random code (e.g., 'A7K2')."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@router.post("/{app_id}/challenges", response_model=ChallengeOut, status_code=201)
def issue_challenge(
    app_id: int,
    req: ChallengeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(lambda: None),  # Optional for now
) -> ChallengeOut:
    """
    Issue a random challenge code for a photo shot.
    
    The code must be written on paper and visible in the photo.
    Code expires in 5 minutes and can only be used once.
    
    Args:
        app_id: Application ID
        req: Challenge request with shot_type
        db: Database session
    
    Returns:
        ChallengeOut with challenge_id, code, and expiry time
    """
    # Check for recent unused challenge (prevent spam)
    five_minutes_ago = utcnow_naive() - timedelta(minutes=5)
    recent_unused = db.query(Challenge).filter(
        Challenge.application_id == app_id,
        Challenge.shot_type == req.shot_type,
        Challenge.used_at.is_(None),
        Challenge.created_at > five_minutes_ago,
    ).first()
    
    if recent_unused:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Challenge already issued for {req.shot_type}. Wait for expiry or use the code.",
        )
    
    # Generate new challenge
    code = generate_challenge_code()
    now = utcnow_naive()
    expires_at = now + timedelta(minutes=5)
    
    challenge = Challenge(
        application_id=app_id,
        shot_type=req.shot_type,
        code=code,
        issued_at=now,
        expires_at=expires_at,
    )
    db.add(challenge)
    db.flush()  # Get the ID
    db.commit()
    
    return ChallengeOut(
        challenge_id=challenge.id,
        code=code,
        issued_at=challenge.issued_at,
        expires_at=expires_at,
    )


@router.get("/{app_id}/challenges/{challenge_id}", response_model=ChallengeOut)
def get_challenge(
    app_id: int,
    challenge_id: int,
    db: Session = Depends(get_db),
) -> ChallengeOut:
    """Get challenge details (for debugging/verification)."""
    challenge = db.query(Challenge).filter(
        Challenge.id == challenge_id,
        Challenge.application_id == app_id,
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    return ChallengeOut(
        challenge_id=challenge.id,
        code=challenge.code,
        issued_at=challenge.issued_at,
        expires_at=challenge.expires_at,
    )
