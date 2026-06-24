import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if not db_url:
    raise RuntimeError("DATABASE_URL is required. Configure the Supabase PostgreSQL connection string.")
if not db_url.startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError("DATABASE_URL must use a PostgreSQL/Supabase connection string.")

# pool_pre_ping avoids reusing stale Supabase pooler connections. Connectivity is
# verified during startup; we must never redirect production data into SQLite.
engine = create_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI dependency that yields a database session and ensures it is closed
    after the request lifecycle is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
