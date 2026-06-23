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
        
        start_ts = int(thirty_days_ago.timestamp())
        to_ts = int(now.timestamp())
        
        from app.integrations.myoperator import fetch_call_logs, get_recording_download_url, download_audio_file
        
        # Paging loop to fetch all logs in the 30-day window
        page = 0
        limit = 100
        synced_count = 0
        
        while True:
            offset = page * limit
            print(f"Fetching call logs page {page} (offset {offset})...")
            try:
                logs_res = fetch_call_logs(start_ts, to_ts, log_from=offset, limit=limit)
            except Exception as e:
                print(f"Failed to fetch call logs page {page}: {e}")
                break
                
            if logs_res.get("status") != "success":
                print(f"MyOperator logs error response: {logs_res.get('message')}")
                break
                
            hits = logs_res.get("data", {}).get("hits", [])
            if not hits:
                print("No more call logs returned from API.")
                break
                
            for hit in hits:
                source = hit.get("_source", {})
                filename = source.get("filename")
                start_time = source.get("start_time")
                caller_number = source.get("caller_number", "Unknown")
                
                if not filename:
                    continue
                    
                # Verify if recording already exists in DB to avoid duplicate syncs
                existing = db.query(db_service.models.AudioFile).filter(
                    db_service.models.AudioFile.filename == filename
                ).first()
                if existing:
                    continue
                    
                print(f"Syncing new recording: {filename} from {caller_number}")
                
                try:
                    # 1. Fetch Temporary Link
                    download_url = get_recording_download_url(filename)
                    
                    # 2. Download File physically
                    local_path = download_audio_file(download_url)
                    file_size = os.path.getsize(local_path)
                    
                    # 3. Save DB Record using call start time as created_at
                    db_file = db_service.models.AudioFile(
                        filename=filename,
                        file_path=local_path,
                        file_size=file_size,
                        mime_type="audio/mpeg",
                        status="pending",
                        created_at=datetime.datetime.utcfromtimestamp(start_time)
                    )
                    db.add(db_file)
                    db.commit()
                    db.refresh(db_file)
                    synced_count += 1
                    
                except Exception as exc:
                    print(f"Failed to sync call log {filename}: {exc}")
                    continue
            
            page += 1
            
        print(f"Successfully synced {synced_count} new call records in database.")

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
