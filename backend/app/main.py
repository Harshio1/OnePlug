import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import engine, Base, SessionLocal
from .routers import auth, transcription
from .services import db_service
from .schemas import UserCreate

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
    allow_origins=["*"],
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
    Runs on FastAPI application boot. Initializes PostgreSQL or SQLite tables,
    and seeds a default administrator employee account if none exists.
    """
    print("Initializing Database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing database tables: {e}")

    # Seed initial employee user for immediate login
    db = SessionLocal()
    try:
        existing_admin = db_service.get_user_by_username(db, "admin")
        if not existing_admin:
            db_service.create_user(
                db=db,
                user_in=UserCreate(
                    username="admin",
                    email="admin@oneplug.ev",
                    password="oneplug2026",
                    full_name="OnePlug Administrator",
                    role="admin"
                )
            )
            print("\n" + "="*50)
            print("   ONEPLUG EV SEED USER REGISTERED SUCCESSFULLY")
            print("   Username: admin")
            print("   Password: oneplug2026")
            print("   Role: admin")
            print("="*50 + "\n")
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
