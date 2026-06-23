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

def get_audio_files(db: Session, skip: int = 0, limit: int = 1000):
    import datetime
    now = datetime.datetime.utcnow()
    # Align to midnight of 30 days ago to include all calls on that calendar day
    thirty_days_ago = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days=30)
    return db.query(models.AudioFile).filter(
        models.AudioFile.created_at >= thirty_days_ago
    ).order_by(models.AudioFile.created_at.desc()).offset(skip).limit(limit).all()

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
        
        # Rename filename to a short 2-3 word summary of the main concern if present
        if analysis:
            desc_text = analysis.get("main_concern") or analysis.get("summary")
            if desc_text:
                # Clean generic customer/caller prefixes
                import re
                desc_clean = desc_text.strip()
                pattern = re.compile(
                    r'^(the\s+)?(customer|caller|user)\s+(experienced|finds|is\s+experiencing|reports|reported|called\s+(to|reporting|about)?|wants\s+to|is|has|complained\s+about|complains\s+about|feels|stated|states)\s+',
                    re.IGNORECASE
                )
                while True:
                    new_desc = pattern.sub('', desc_clean)
                    if new_desc == desc_clean:
                        break
                    desc_clean = new_desc.strip()
                
                desc_clean = re.sub(r'^(that|about|to|with|for|on|a|an|the)\s+', '', desc_clean, flags=re.IGNORECASE).strip()
                
                # Remove punctuation and split into words
                words = [w.strip(".,?!();:\"'") for w in desc_clean.split() if w.strip()]
                short_desc = " ".join(words[:3]) # Take first 3 words
                if short_desc:
                    ext = os.path.splitext(db_file.filename)[1] or ".mp3"
                    db_file.filename = f"{short_desc}{ext}"

    db.commit()
    db.refresh(db_transcript)
    return db_transcript
