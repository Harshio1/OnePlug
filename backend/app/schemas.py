from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Token & Authentication Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "agent"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Segment Schema (Nested inside Transcript) ---
class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    avg_logprob: Optional[float] = None
    compression_ratio: Optional[float] = None
    no_speech_prob: Optional[float] = None
    speaker: Optional[str] = None  # Future proof for diarization

# --- Transcript Schemas ---
class TranscriptResponse(BaseModel):
    id: str
    audio_file_id: str
    text: str
    language: Optional[str] = None
    words_count: int
    duration: float
    segments: Optional[List[Dict[str, Any]]] = None
    segment_count: Optional[int] = None
    translated_text: Optional[str] = None          # Full English translation
    translated_segments: Optional[List[Dict[str, Any]]] = None  # Per-segment translations
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Audio File Schemas ---
class CustomerResponse(BaseModel):
    id: int
    mobile_number: str
    customer_name: Optional[str] = None
    register_no: Optional[str] = None
    station_name: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    start_soc: Optional[str] = None
    end_soc: Optional[str] = None
    total_units: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_modal: Optional[str] = None
    charger_ownership: Optional[str] = None
    rating_feedback: Optional[str] = None
    last_transaction_date: Optional[str] = None
    number_of_rating_stars: Optional[str] = None
    rating_comments: Optional[str] = None
    agent_name: Optional[str] = None
    class Config:
        from_attributes = True

class AudioFileResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    duration: Optional[float] = None
    mime_type: str
    status: str
    caller_number: Optional[str] = None
    agent_name: Optional[str] = None
    call_direction: Optional[str] = None
    error_message: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime
    transcript: Optional[TranscriptResponse] = None
    customers: Optional[List[CustomerResponse]] = None

    class Config:
        from_attributes = True

class TranscriptListResponse(BaseModel):
    id: str
    audio_file_id: str
    language: Optional[str] = None
    words_count: int
    duration: float
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AudioFileListResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    duration: Optional[float] = None
    mime_type: str
    status: str
    caller_number: Optional[str] = None
    agent_name: Optional[str] = None
    call_direction: Optional[str] = None
    error_message: Optional[str] = None
    uploaded_by_id: Optional[int] = None
    created_at: datetime
    transcript: Optional[TranscriptListResponse] = None
    customers: Optional[List["CustomerResponse"]] = None

    class Config:
        from_attributes = True

# --- Transcription Job Configuration ---
class TranscriptionConfigRequest(BaseModel):
    language_hint: Optional[str] = Field(None, description="Language hint, e.g. 'ta' for Tamil, 'en' for English, or leave empty for auto-detect.")
    prompt: Optional[str] = Field(None, description="Optional text context to guide the Whisper style, helpful for acronyms or mixed vocabulary.")
