import sys
import os
import datetime

# Adjust python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service
from app.routers.transcription import process_transcription_task

def main():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        five_days_ago = now - datetime.timedelta(days=5)
        print(f"Checking for calls since: {five_days_ago} UTC")

        # Find all files in the last 5 days that are not completed
        # Status can be pending, failed, or processing
        files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.created_at >= five_days_ago,
            db_service.models.AudioFile.status != "completed"
        ).order_by(db_service.models.AudioFile.created_at.desc()).all()

        total_files = len(files)
        print(f"Found {total_files} files that need transcription.")

        if total_files == 0:
            print("No files to transcribe.")
            return

        for idx, file in enumerate(files, 1):
            print(f"[{idx}/{total_files}] Processing ID: {file.id} | Filename: {file.filename} | Status: {file.status} | Created At: {file.created_at}")
            try:
                process_transcription_task(file.id)
                db.refresh(file)
                print(f" -> Finished. Status: {file.status}")
            except Exception as e:
                print(f" -> Error: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
