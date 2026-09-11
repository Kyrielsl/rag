from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import generate_api_key, hash_api_key
from app.db.session import get_db
from app.models.auth import ApiKey, ApiKeyDomainGrant, User, UserDomainGrant
from app.models.domain import Domain
from app.schemas.auth import ApiKeyCreateIn, ApiKeyOut, GrantIn
from app.schemas.console import ApiKeyListItem

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/api-keys", response_model=list[ApiKeyListItem])
def list_api_keys(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[ApiKeyListItem]:
    keys = db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc())).all()
    return [
        ApiKeyListItem(
            id=k.id,
            name=k.name,
            scope=k.scope,
            status=k.status,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("/api-keys", response_model=ApiKeyOut)
def create_api_key(
    body: ApiKeyCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    raw = generate_api_key()
    key = ApiKey(name=body.name, key_hash=hash_api_key(raw), scope=body.scope)
    db.add(key)
    db.commit()
    db.refresh(key)
    return ApiKeyOut(id=key.id, name=key.name, scope=key.scope, key=raw)


@router.post("/api-key-grants/{api_key_id}")
def grant_api_key_domain(
    api_key_id: str,
    body: GrantIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    key = db.get(ApiKey, api_key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="api key not found")
    domain = db.scalar(select(Domain).where(Domain.name == body.domain))
    if domain is None:
        raise HTTPException(status_code=404, detail="domain not found")

    exists = db.scalar(
        select(ApiKeyDomainGrant).where(
            ApiKeyDomainGrant.api_key_id == api_key_id,
            ApiKeyDomainGrant.domain_id == domain.id,
        )
    )
    if exists is None:
        db.add(ApiKeyDomainGrant(api_key_id=api_key_id, domain_id=domain.id))
        db.commit()
    return {"status": "granted", "api_key_id": api_key_id, "domain": body.domain}


@router.post("/user-grants/{username}")
def grant_user_domain(
    username: str,
    body: GrantIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    domain = db.scalar(select(Domain).where(Domain.name == body.domain))
    if domain is None:
        raise HTTPException(status_code=404, detail="domain not found")

    exists = db.scalar(
        select(UserDomainGrant).where(
            UserDomainGrant.user_id == user.id,
            UserDomainGrant.domain_id == domain.id,
        )
    )
    if exists is None:
        db.add(UserDomainGrant(user_id=user.id, domain_id=domain.id))
        db.commit()
    return {"status": "granted", "username": username, "domain": body.domain}