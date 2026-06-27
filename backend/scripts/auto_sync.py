import sys, os, datetime, time
sys.path.append('/var/www/oneplug/backend')
os.chdir('/var/www/oneplug/backend')

from dotenv import load_dotenv
load_dotenv('/var/www/oneplug/backend/.env')

# Lock file to prevent multiple instances
LOCK_FILE = '/tmp/auto_sync.lock'
if os.path.exists(LOCK_FILE):
    print(f"Another instance is running. Exiting.")
    sys.exit(0)

try:
    open(LOCK_FILE, 'w').write(str(os.getpid()))

    from app.db import SessionLocal
    from app.services import db_service
    from app.routers.transcription import process_transcription_task
    from app.integrations.myoperator import fetch_call_logs, get_recording_download_url, download_audio_file

    today = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).date()
    start_ts = int((datetime.datetime(today.year, today.month, today.day, 0, 0, 0) - datetime.timedelta(hours=5, minutes=30)).timestamp())
    to_ts = int(datetime.datetime.utcnow().timestamp())

    print(f"[{datetime.datetime.now()}] Auto-sync started for {today}")

    db = SessionLocal()
    try:
        page, limit, synced_count = 0, 100, 0

        while True:
            offset = page * limit
            logs_res = fetch_call_logs(start_ts, to_ts, log_from=offset, limit=limit)
            if logs_res.get("status") != "success": break
            hits = logs_res.get("data", {}).get("hits", [])
            if not hits: break

            for hit in hits:
                source = hit.get("_source", {})
                filename = source.get("filename")
                start_time = source.get("start_time")
                caller_number = source.get("caller_number", "Unknown")
                if not filename: continue

                existing = db.query(db_service.models.AudioFile).filter(
                    db_service.models.AudioFile.filename == filename
                ).first()
                if existing: continue

                print(f"New call: {filename} from {caller_number}")
                try:
                    download_url = get_recording_download_url(filename)
                    local_path = download_audio_file(download_url)
                    file_size = os.path.getsize(local_path)
                    db_file = db_service.models.AudioFile(
                        filename=filename, file_path=local_path,
                        file_size=file_size, mime_type="audio/mpeg",
                        status="pending",
                        created_at=datetime.datetime.utcfromtimestamp(start_time) + datetime.timedelta(hours=5, minutes=30)
                    )
                    db.add(db_file)
                    db.commit()
                    db.refresh(db_file)
                    synced_count += 1
                except Exception as exc:
                    print(f"Failed: {exc}")
                    continue
            page += 1

        print(f"Synced {synced_count} new calls.")

        pending_files = db.query(db_service.models.AudioFile).filter(
            db_service.models.AudioFile.status == "pending"
        ).order_by(db_service.models.AudioFile.created_at.asc()).all()

        total = len(pending_files)
        if total > 0:
            print(f"Transcribing {total} pending files...")
            for idx, file in enumerate(pending_files, 1):
                print(f"[{idx}/{total}] Transcribing: {file.filename}...")
                try:
                    process_transcription_task(file.id)
                    db.refresh(file)
                    print(f"  -> Done!")
                except Exception as e:
                    print(f"  -> Error: {e}")
                time.sleep(1)
        else:
            print("No pending files.")

    finally:
        db.close()

finally:
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

print(f"[{datetime.datetime.now()}] Auto-sync complete.")
