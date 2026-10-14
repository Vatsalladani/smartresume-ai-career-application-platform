from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings, normalize_database_url


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = normalize_database_url(settings.database_url)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    import os
    if os.environ.get("TESTING") == "1":
        import sys
        for mod_name in ("tests.conftest", "backend.tests.conftest", "conftest"):
            if mod_name in sys.modules:
                mod = sys.modules[mod_name]
                if hasattr(mod, "TestingSessionLocal"):
                    return mod.TestingSessionLocal()
        try:
            from tests.conftest import TestingSessionLocal
            return TestingSessionLocal()
        except Exception:
            pass
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = get_session()
    try:
        yield db
    finally:
        db.close()

