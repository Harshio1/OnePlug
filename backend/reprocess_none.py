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
        files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.status == "completed",
            db_service.models.AudioFile.filename.like("%None%")
        ).all()

        print(f"Found {len(files)} files to re-process.")

        for idx, file in enumerate(files, 1):
            # Find the corresponding transcript
            transcript = db.query(db_service.models.Transcript).filter(
                db_service.models.Transcript.audio_file_id == file.id
            ).first()

            if not transcript:
                print(f"[{idx}] No transcript for file {file.id}")
                continue

            print(f"[{idx}] Re-analyzing file {file.id}...")
            
            try:
                # Run Gemini analysis
                analysis = gemini.process_transcript(transcript.text)
                if analysis:
                    transcript.analysis = analysis
                    
                    # Update filename
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
                            print(f" -> Updated filename to: {file.filename}")
                    
                    db.commit()
                else:
                    print(" -> Gemini returned empty analysis.")
            except Exception as e:
                print(f" -> Failed to re-analyze: {e}")
            
            # Wait 10 seconds between files to avoid hitting the rate limit
            time.sleep(10)

    finally:
        db.close()

if __name__ == "__main__":
    main()
