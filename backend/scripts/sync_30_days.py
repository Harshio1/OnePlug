import sys
import os
import datetime
import time

# Adjust python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.services import db_service
from app.routers.transcription import process_transcription_task

def main():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        thirty_days_ago = now - datetime.timedelta(days=30)
        
        print(f"[{now}] Starting full 30-day historical import...")
        print(f"Fetching call logs from MyOperator since: {thirty_days_ago} UTC...")
        
        # 1. Trigger the sync process to fetch logs and download audio files from MyOperator for 30 days
        # We pass the start timestamp to pull the last 30 days
        start_ts = int(thirty_days_ago.timestamp())
        
        # Pull call logs into database (this will register the metadata in Supabase and download files to disk)
        from app.integrations.myoperator import MyOperatorClient
        client = MyOperatorClient()
        logs = client.fetch_call_logs(from_ts=start_ts, limit=1000)
        
        print(f"Retrieved {len(logs)} call logs from MyOperator.")
        
        # Process and save them to the database
        synced_count = 0
        for log in logs:
            try:
                # Add to DB if not exists
                db_file = client.save_log_to_db(db, log)
                if db_file:
                    synced_count += 1
            except Exception as e:
                print(f"Error saving log: {e}")
                
        print(f"Successfully synced {synced_count} call records in database.")

        # 2. Transcribe the pending calls
        # We query for all pending files from the last 30 days
        pending_files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.created_at >= thirty_days_ago,
            db_service.models.AudioFile.status != "completed"
        ).order_by(db_service.models.AudioFile.created_at.asc()).all()

        total = len(pending_files)
        print(f"Found {total} files that need transcription.")

        for idx, file in enumerate(pending_files, 1):
            print(f"[{idx}/{total}] Transcribing call ID: {file.id} | Filename: {file.filename}...")
            try:
                # Runs Whisper local CPU transcription and Gemini analysis
                process_transcription_task(file.id)
                db.refresh(file)
                print(f"  -> Finished! Status: {file.status} | Filename: {file.filename}")
            except Exception as e:
                print(f"  -> Error transcribing file: {e}")
            
            # Wait 15 seconds to avoid Gemini rate limits during analysis
            time.sleep(15)

    finally:
        db.close()

if __name__ == "__main__":
    main()
