import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service
from app.routers.transcription import process_transcription_task

def main():
    db = SessionLocal()
    try:
        # Find file starting with the user's pattern
        pattern = "079cb94a23436399206203538689de7e4041f2448d8fd18"
        file = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.filename.like(f"{pattern}%")
        ).first()

        if not file:
            print(f"File starting with {pattern} not found in database.")
            return

        print(f"Found file: {file.filename} | Current status: {file.status}")

        # Delete any existing transcript first so process_transcription_task can write a new one
        if file.transcript:
            print("Deleting existing transcript...")
            db.delete(file.transcript)
            db.commit()

        # Update status back to pending
        file.status = "pending"
        db.commit()

        print("Triggering re-transcription with new prompt bias...")
        process_transcription_task(file.id)

        # Refresh
        db.refresh(file)
        print(f"Re-transcription finished! Status: {file.status}")
        if file.transcript:
            print("\nNew Transcript Text:")
            print(file.transcript.text)
            if file.transcript.analysis:
                print("\nNew Analysis Summary:")
                print(file.transcript.analysis.summary)
                print("Issue Type:", file.transcript.analysis.issue_type)
        else:
            print("Error: No transcript created.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
