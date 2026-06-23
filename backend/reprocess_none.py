import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service
from app.services.gemini_service import GeminiService

def main():
    db = SessionLocal()
    gemini = GeminiService()
    try:
        # Find all completed audio files named "None.mp3" or containing "None"
        from sqlalchemy import or_
        fallback_keywords = ["None", "charging session issue", "support inquiry", "app login issue", "refund payment issue", "rfid card setup"]
        filters = [db_service.models.AudioFile.filename.like(f"%{kw}%") for kw in fallback_keywords]

        files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.status == "completed",
            or_(*filters)
        ).all()

        total = len(files)
        print(f"Found {total} files that need Gemini/Azure AI analysis.")

        for idx, file in enumerate(files, 1):
            # Find the corresponding transcript
            transcript = db.query(db_service.models.Transcript).filter(
                db_service.models.Transcript.audio_file_id == file.id
            ).first()

            if not transcript or not transcript.text:
                print(f"[{idx}/{total}] No transcript text for file {file.id}")
                continue

            print(f"[{idx}/{total}] Sending to AI Engine: {file.id}...")
            
            # Retry loop
            analysis = None
            for attempt in range(3):
                try:
                    analysis = gemini.process_transcript(transcript.text)
                    # Check if it returned local fallback
                    if analysis and any(kw in analysis.get("summary", "") for kw in ["Support call regarding", "fallback"]):
                        print(f"   -> Local fallback detected. Pausing for 5 seconds (Attempt {attempt+1}/3)...")
                        time.sleep(5)
                        continue
                    break
                except Exception as e:
                    print(f"   -> Error on attempt {attempt+1}: {e}. Retrying in 5s...")
                    time.sleep(5)

            if analysis:
                transcript.analysis = analysis
                
                # Update filename with clean summarized concern
                desc_text = analysis.get("main_concern") or analysis.get("summary")
                if desc_text:
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
                    words = [w.strip(".,?!();:\"'") for w in desc_clean.split() if w.strip()]
                    short_desc = " ".join(words[:3])
                    
                    if short_desc:
                        file.filename = f"{short_desc}.mp3"
                        print(f"   -> Success! Filename: {file.filename}")
                
                db.commit()
            else:
                print("   -> Failed to get analysis after retries.")
            
            # Wait 1 second between files (no Azure rate limits)
            time.sleep(1)

    finally:
        db.close()

if __name__ == "__main__":
    main()
