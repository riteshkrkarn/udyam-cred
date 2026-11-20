"""UdyamCred FastAPI application (Stage 1 + Stage 2).

Stage 1:
  - Health, auth (JWT access + DB-stored rotating refresh + remember-me)
  - Verification endpoint that runs stock reconciliation

Stage 2:
  - Application workflow (create, get, list, update status)
  - Scoring orchestration (all engines in sequence)
  - Replay and override functionality
  - Document upload and household data management
  - Consent tracking and audit trail

Run the app:
    uvicorn main:app --reload
Set up the database first with:
    python scripts/seed.py
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    create_refresh_token_value,
    decode_token,
    hash_password,
    hash_token,
    refresh_expiry,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import RefreshToken, User
from app.policy import load_policy
from app.reconciliation import reconcile
from app.schemas import (
    HealthOut,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    ReconciliationOut,
    RegisterRequest,
    ShopIn,
    TokenResponse,
    UserOut,
)
from app.utils import utcnow_naive
from app.endpoints import scoring, applications, consent, documents, household, audit

app = FastAPI(title="UdyamCred", version="0.2.0", description="Stage 2 backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", version=app.version)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id = int(payload.get("sub"))
    except Exception:
        raise credentials_exc
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise credentials_exc
    return user


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    if db.query(User).filter_by(email=req.email).first():
        raise HTTPException(status_code=409, detail="email already registered")
    if req.role not in {"borrower", "officer", "approver", "auditor"}:
        raise HTTPException(status_code=400, detail="invalid role")
    user = User(email=req.email, password_hash=hash_password(req.password), role=req.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, email=user.email, role=user.role)


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter_by(email=req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    access = create_access_token(user.id)
    refresh_val = create_refresh_token_value()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_val),
        expires_at=refresh_expiry(req.remember_me),
        remember_me=req.remember_me,
    )
    db.add(rt)
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_val,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/auth/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Rotate a refresh token: revoke the old one, issue a new access + refresh."""
    rt = (
        db.query(RefreshToken)
        .filter_by(token_hash=hash_token(req.refresh_token), revoked=False)
        .first()
    )
    now = utcnow_naive()
    if rt is None or rt.expires_at < now:
        raise HTTPException(status_code=401, detail="invalid or expired refresh token")

    rt.revoked = True
    new_val = create_refresh_token_value()
    new_rt = RefreshToken(
        user_id=rt.user_id,
        token_hash=hash_token(new_val),
        expires_at=refresh_expiry(rt.remember_me),
        remember_me=rt.remember_me,
    )
    db.add(new_rt)
    db.flush()  # populate new_rt.id
    rt.replaced_by = new_rt.id
    db.commit()

    user = db.query(User).filter_by(id=rt.user_id).first()
    access = create_access_token(user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=new_val,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/auth/logout")
def logout(req: LogoutRequest, db: Session = Depends(get_db)) -> dict:
    rt = db.query(RefreshToken).filter_by(
        token_hash=hash_token(req.refresh_token), revoked=False
    ).first()
    if rt is not None:
        rt.revoked = True
        db.commit()
    return {"revoked": rt is not None}


@app.post("/reconcile", response_model=ReconciliationOut)
def reconcile_endpoint(
    shop_in: ShopIn,
    current_user: User = Depends(get_current_user),
) -> ReconciliationOut:
    """Run stock reconciliation on a submitted shop and return the verdict."""
    policy = load_policy()
    result = reconcile(shop_in.model_dump(), policy)
    return ReconciliationOut(**result)


@app.get("/shops/me")
def whoami(current_user: User = Depends(get_current_user)) -> dict:
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}


# ============================================================================
# Stage 2 Routers
# ============================================================================

app.include_router(scoring.router)
app.include_router(applications.router)
app.include_router(consent.router)
app.include_router(documents.router)
app.include_router(household.router)
app.include_router(audit.router)
