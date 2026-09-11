from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, hash_api_key
from app.db.session import get_db
from app.models.auth import ApiKey, ApiKeyDomainGrant, User, UserDomainGrant
from app.models.domain import Domain, utcnow


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization header")
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    user = db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


def get_optional_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> ApiKey | None:
    if x_api_key is None:
        return None
    key = db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(x_api_key),
            ApiKey.status == "active",
        )
    )
    if key is None:
        raise HTTPException(status_code=401, detail="invalid api key")
    if key.expires_at is not None and key.expires_at < utcnow():
        raise HTTPException(status_code=401, detail="api key expired")
    return key


def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user


def require_upload_access(
    user: User | None = Depends(get_optional_user),
    api_key: ApiKey | None = Depends(get_optional_api_key),
) -> None:
    if user is not None and user.role == "admin":
        return
    if api_key is not None and api_key.scope == "upload":
        return
    raise HTTPException(status_code=403, detail="upload access required")


def ensure_search_access(user: User | None, api_key: ApiKey | None) -> None:
    if user is not None:
        return
    if api_key is not None and api_key.scope == "search":
        return
    raise HTTPException(status_code=403, detail="search access required")


def allowed_domain_ids(db: Session, user: User | None, api_key: ApiKey | None) -> set[str]:
    domains = {d.id: d for d in db.scalars(select(Domain)).all()}
    allowed = {did for did, d in domains.items() if not d.is_sensitive}

    if user is not None and user.role == "admin":
        return set(domains)

    granted: set[str] = set()
    if user is not None:
        granted = {g.domain_id for g in db.scalars(select(UserDomainGrant).where(UserDomainGrant.user_id == user.id)).all()}
    if api_key is not None:
        granted |= {g.domain_id for g in db.scalars(select(ApiKeyDomainGrant).where(ApiKeyDomainGrant.api_key_id == api_key.id)).all()}

    allowed |= granted & set(domains)
    return allowed