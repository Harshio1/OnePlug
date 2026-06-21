import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service
from app.routers.transcription import process_transcription_task

def main():
    db = SessionLocal()
    try:
        pattern = "079cb94a23436399206203538689de7e4041f2448d8fd18"
        files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.filename.like(f"{pattern}%")
        ).all()

        print(f"Found {len(files)} files with prefix {pattern}.")

        for file in files:
            # Skip if completed and already has a transcript
            if file.status == "completed" and file.transcript:
                print(f"File {file.filename} is already completed. Transcript: {file.transcript.text[:100]}...")
                continue
            
            # Reset status to pending
            print(f"Transcribing {file.filename} (Current status: {file.status})...")
            if file.transcript:
                db.delete(file.transcript)
                db.commit()
            file.status = "pending"
            db.commit()

            try:
                process_transcription_task(file.id)
                db.refresh(file)
                print(f" -> Finished. Status: {file.status}")
                if file.transcript:
                    print(f" -> Transcript: {file.transcript.text[:200]}...")
            except Exception as e:
                print(f" -> Error: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
