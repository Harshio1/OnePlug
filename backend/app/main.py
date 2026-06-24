import os
import logging
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import engine, Base, SessionLocal
from .routers import auth, transcription
from .services import db_service
from .schemas import UserCreate

logger = logging.getLogger(__name__)

# Create upload folder on launch
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise transcription platform for OnePlug EV customer call audio files.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS middleware for secure Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(transcription.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def on_startup():
    """
    Runs on FastAPI application boot. Verifies Supabase PostgreSQL and creates
    tables. Administrator bootstrap is explicit and opt-in.
    """
    settings.validate_runtime_configuration()
    print("Initializing Supabase PostgreSQL tables...")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")
    except Exception as e:
        logger.exception("Error initializing database tables.")
        raise RuntimeError("Database initialization failed.") from e

    if not all((settings.BOOTSTRAP_ADMIN_USERNAME, settings.BOOTSTRAP_ADMIN_EMAIL, settings.BOOTSTRAP_ADMIN_PASSWORD)):
        return

    # Seed only an explicitly configured initial administrator.
    db = SessionLocal()
    try:
        existing_admin = db_service.get_user_by_username(db, settings.BOOTSTRAP_ADMIN_USERNAME)
        if not existing_admin:
            db_service.create_user(
                db=db,
                user_in=UserCreate(
                    username=settings.BOOTSTRAP_ADMIN_USERNAME,
                    email=settings.BOOTSTRAP_ADMIN_EMAIL,
                    password=settings.BOOTSTRAP_ADMIN_PASSWORD,
                    full_name="OnePlug Administrator",
                    role="admin"
                )
            )
            print("Bootstrap administrator registered successfully.")
        else:
            print("Admin employee already seeded.")
    except Exception as e:
        print(f"Error seeding initial employee account: {e}")
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "api_documentation": "/docs"
    }
