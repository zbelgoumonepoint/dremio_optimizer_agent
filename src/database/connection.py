"""Database connection management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from ..config.settings import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=settings.debug)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Session:
    """Get database session context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables."""
    from .models import Base

    Base.metadata.create_all(bind=engine)
