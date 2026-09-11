from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.uploads import router as uploads_router
from app.config import get_settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.auth import User
from app.services.classification import ensure_default_domains
from app.storage import get_storage


def ensure_admin(db) -> None:
    settings = get_settings()
    exists = db.scalar(select(User).where(User.username == settings.admin_username))
    if exists is None:
        db.add(
            User(
                username=settings.admin_username,
                hashed_password=hash_password(settings.admin_password),
                role="admin",
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_storage().ensure_bucket()
    with SessionLocal() as db:
        ensure_default_domains(db)
        ensure_admin(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(uploads_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(search_router)
    return app


app = create_app()