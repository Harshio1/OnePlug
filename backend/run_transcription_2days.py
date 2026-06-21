import sys
import os
import datetime
import time

# Adjust python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service
from app.routers.transcription import process_transcription_task

def main():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        two_days_ago = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days=2)
        print(f"Starting batch transcription for the last 2 days (since {two_days_ago} UTC)...")

        # Find all files in the last 2 days that are not completed
        files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.created_at >= two_days_ago,
            db_service.models.AudioFile.status != "completed"
        ).order_by(db_service.models.AudioFile.created_at.desc()).all()

        total_files = len(files)
        print(f"Found {total_files} files that need transcription.")

        if total_files == 0:
            print("All files in the last 2 days are already completed!")
            return

        for idx, file in enumerate(files, 1):
            print(f"[{idx}/{total_files}] Processing ID: {file.id} | Filename: {file.filename} | Status: {file.status}")
            
            # Reset status to pending to ensure it is processed
            file.status = "pending"
            db.commit()

            try:
                process_transcription_task(file.id)
                db.refresh(file)
                print(f" -> Finished. Status: {file.status}")
            except Exception as e:
                print(f" -> Error: {e}")

            # Sleep 10 seconds to respect Gemini API rate limits and keep CPU cooler
            print("Sleeping for 10 seconds to respect API limits...")
            time.sleep(10)

    finally:
        db.close()

if __name__ == "__main__":
    main()
