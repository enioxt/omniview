"""SQLAlchemy engine + session factory.

Uses SQLite with WAL mode for better concurrent reads.
Ready to swap to PostgreSQL by changing DATABASE_URL.
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.debug,
)

# Enable WAL mode for SQLite
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_conn: object, _: object) -> None:
        cursor = dbapi_conn.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():  # type: ignore[return]
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (used in tests and dev startup)."""
    Base.metadata.create_all(bind=engine)
