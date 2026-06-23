import sys
import os
import datetime

# Adjust python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.services import db_service

def cleanup_old_records():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        thirty_days_ago = now - datetime.timedelta(days=30)
        print(f"[{now}] Starting history cleanup...")
        print(f"Target date threshold (older than 30 days): {thirty_days_ago} UTC")

        # 1. Fetch all records older than 30 days
        old_files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.created_at < thirty_days_ago
        ).all()

        count = len(old_files)
        print(f"Found {count} records older than 30 days.")

        if count == 0:
            print("No old records to clean up.")
            return

        deleted_files_count = 0
        for idx, file in enumerate(old_files, 1):
            print(f"[{idx}/{count}] Cleaning up Call ID: {file.id} | Date: {file.created_at}")

            # Delete the local audio file from the VM disk
            if file.file_path and os.path.exists(file.file_path):
                try:
                    os.remove(file.file_path)
                    print(f"  -> Deleted audio file from disk: {file.file_path}")
                    deleted_files_count += 1
                except Exception as fe:
                    print(f"  -> Error deleting file from disk: {fe}")

            # Delete the database entries (cascade deletes the corresponding transcript)
            try:
                db.delete(file)
                print(f"  -> Deleted database metadata record.")
            except Exception as de:
                print(f"  -> Error deleting database record: {de}")

        db.commit()
        print(f"Successfully deleted {deleted_files_count} audio files and {count} database records.")

    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_records()
