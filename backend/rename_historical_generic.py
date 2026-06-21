import os
import sys
import re

# Add backend directory to path
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import models

DATABASE_URL = "sqlite:///oneplug_fallback.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def clean_desc(desc_text: str) -> str:
    if not desc_text:
        return ""
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
    return desc_clean

def run():
    db = SessionLocal()
    try:
        audio_files = db.query(models.AudioFile).all()
        renamed_count = 0
        for f in audio_files:
            if not f.transcript or not f.transcript.analysis:
                continue
            
            analysis = f.transcript.analysis
            desc_text = analysis.get("main_concern") or analysis.get("summary")
            if not desc_text:
                continue
                
            desc_clean = clean_desc(desc_text)
            words = [w.strip(".,?!();:\"'") for w in desc_clean.split() if w.strip()]
            short_desc = " ".join(words[:3]) # Take first 3 words
            
            if short_desc:
                ext = os.path.splitext(f.filename)[1] or ".mp3"
                new_filename = f"{short_desc}{ext}"
                if f.filename != new_filename:
                    print(f"Renaming: '{f.filename}' -> '{new_filename}' (from: '{desc_text}')")
                    f.filename = new_filename
                    renamed_count += 1
                    
        db.commit()
        print(f"Successfully updated {renamed_count} files in the database.")
    finally:
        db.close()

if __name__ == "__main__":
    run()
