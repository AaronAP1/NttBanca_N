import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.api.routes import files, health, items
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.db_auto_create_tables:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Tablas verificadas/creadas en Postgres")
        except SQLAlchemyError:
            # No tumbamos la app: /health/db mostrará el problema de conexión.
            logger.exception("No se pudo conectar a Postgres para crear las tablas")
    yield
    engine.dispose()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(health.router)
app.include_router(items.router)
app.include_router(files.router)
