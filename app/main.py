from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.api.health import router as health_router
from app.api.uploads import router as uploads_router
from app.config import get_settings
from app.db.session import Base, engine
from app.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_storage().ensure_bucket()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(uploads_router)
    return app


app = create_app()