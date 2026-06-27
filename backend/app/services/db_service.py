from sqlalchemy.orm import Session
from .. import models, schemas
from passlib.context import CryptContext
import os
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- User CRUD ---
def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed_pw = get_password_hash(user_in.password)
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- AudioFile CRUD ---
def create_audio_file(
    db: Session, 
    filename: str, 
    file_path: str, 
    file_size: int, 
    mime_type: str, 
    user_id: int = None
) -> models.AudioFile:
    db_file = models.AudioFile(
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        status="pending",
        uploaded_by_id=user_id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def update_audio_file_status(
    db: Session, 
    file_id: str, 
    status: str, 
    error_message: str = None, 
    duration: float = None
) -> models.AudioFile:
    db_file = db.query(models.AudioFile).filter(models.AudioFile.id == file_id).first()
    if db_file:
        db_file.status = status
        if error_message:
            db_file.error_message = error_message
        if duration:
            db_file.duration = duration
        db.commit()
        db.refresh(db_file)
    return db_file

def get_audio_file(db: Session, file_id: str) -> models.AudioFile:
    return db.query(models.AudioFile).filter(models.AudioFile.id == file_id).first()

def get_audio_files(db: Session, skip: int = 0, limit: int = 1000, uploaded_by_id: int = None):
    import datetime
    now = datetime.datetime.utcnow()
    # Align to midnight of 30 days ago to include all calls on that calendar day
    thirty_days_ago = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days=30)
    query = db.query(models.AudioFile).filter(models.AudioFile.created_at >= thirty_days_ago)
    if uploaded_by_id is not None:
        query = query.filter(models.AudioFile.uploaded_by_id == uploaded_by_id)
    return query.order_by(models.AudioFile.created_at.desc()).offset(skip).limit(limit).all()

# --- Transcript CRUD ---
def create_transcript(
    db: Session,
    audio_file_id: str,
    text: str,
    language: str,
    words_count: int,
    duration: float,
    segments: list,
    segment_count: int = 0,
    analysis: dict = None,
    translated_text: str = None,
    translated_segments: list = None,
) -> models.Transcript:
    logger.info(
        f"db_service.create_transcript | audio_id={audio_file_id} | "
        f"language={language} | duration={duration:.2f}s | "
        f"words={words_count} | segments={segment_count} | "
        f"translated={'yes' if translated_text else 'no'}"
    )
    db_transcript = models.Transcript(
        audio_file_id=audio_file_id,
        text=text,
        language=language,
        words_count=words_count,
        duration=duration,
        segments=segments,
        analysis=analysis,
        translated_text=translated_text,
        translated_segments=translated_segments,
    )
    db.add(db_transcript)

    db_file = db.query(models.AudioFile).filter(models.AudioFile.id == audio_file_id).first()
    if db_file:
        db_file.status = "completed"
        db_file.duration = duration
        
        # Preserve the upstream filename. MyOperator uses it as the durable
        # external identifier for idempotent syncs; presentation labels belong
        # in a separate field, not in the source identifier.

    db.commit()
    db.refresh(db_transcript)
    return db_transcript
