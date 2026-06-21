import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

logger = logging.getLogger(__name__)

# Parse database url. Support SQLite fallback for local testing if desired,
# but default to production-ready PostgreSQL with pool settings.
db_url = settings.DATABASE_URL

# For SQLite, we need check_same_thread=False. For PostgreSQL, we omit it.
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

try:
    # pool_pre_ping=True automatically tests connections before sending queries
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10 if not db_url.startswith("sqlite") else None,
        max_overflow=20 if not db_url.startswith("sqlite") else None
    )
    # Eagerly test the database connection to verify if PostgreSQL is online
    with engine.connect() as conn:
        pass
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to initialize database engine with URL {db_url}: {e}")
    # Fallback to a local SQLite for absolute resilience if PostgreSQL is offline
    logger.info("Falling back to local SQLite database 'oneplug_fallback.db' for development testing...")
    fallback_url = "sqlite:///./oneplug_fallback.db"
    engine = create_engine(fallback_url, connect_args={"check_same_thread": False})
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
