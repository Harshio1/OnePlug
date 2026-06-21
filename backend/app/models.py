import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .db import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="agent", nullable=False)  # admin, agent, manager
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    audio_files = relationship("AudioFile", back_populates="uploader")

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # In bytes
    duration = Column(Float, nullable=True)       # In seconds, determined post-processing
    mime_type = Column(String, nullable=False)    # audio/mpeg, audio/wav, etc.
    status = Column(String, default="pending", nullable=False)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    uploader = relationship("User", back_populates="audio_files")
    transcript = relationship("Transcript", back_populates="audio_file", uselist=False, cascade="all, delete-orphan")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    audio_file_id = Column(String, ForeignKey("audio_files.id", ondelete="CASCADE"), unique=True, nullable=False)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)          # Detected or selected language (e.g. "ta", "en")
    words_count = Column(Integer, default=0, nullable=False)
    duration = Column(Float, default=0.0, nullable=False)
    
    # Store detailed segments with timestamps: [{start: 0.0, end: 2.5, text: "..."}]
    segments = Column(JSON, nullable=True)

    # Per-segment English translations [{start, end, text}] for Tamil audio
    translated_segments = Column(JSON, nullable=True)

    # Full English translation of Tamil transcript
    translated_text = Column(Text, nullable=True)

    # AI analysis block: summary, issue detection, sentiment
    analysis = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relationships
    audio_file = relationship("AudioFile", back_populates="transcript")
