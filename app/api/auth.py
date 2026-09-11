from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.auth import User
from app.schemas.auth import LoginIn, TokenOut
from app.services.audit import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.hashed_password):
        write_audit(db, action="login", subject=body.username, result="failed")
        db.commit()
        raise HTTPException(status_code=401, detail="invalid username or password")
    write_audit(db, action="login", subject=user.username)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role))