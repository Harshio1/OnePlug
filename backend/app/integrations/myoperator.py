import os
import json
import time
import uuid
import logging
import requests
import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AudioFile
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

# State tracking file path
STATE_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "myoperator_sync_state.json")

def get_last_sync_timestamp() -> int:
    """Read the last synced Unix timestamp from local state file, default to 30 days ago."""
    now_ts = int(time.time())
    thirty_days_ago = now_ts - (30 * 24 * 60 * 60)
    
    if os.path.exists(STATE_FILE_PATH):
        try:
            with open(STATE_FILE_PATH, "r") as f:
                state = json.load(f)
                return state.get("last_sync_timestamp", thirty_days_ago)
        except Exception as e:
            logger.error(f"Failed to read MyOperator state file: {e}")
            
    return thirty_days_ago

def save_last_sync_timestamp(timestamp: int):
    """Write the last synced Unix timestamp to local state file."""
    try:
        with open(STATE_FILE_PATH, "w") as f:
            json.dump({"last_sync_timestamp": timestamp}, f)
    except Exception as e:
        logger.error(f"Failed to write MyOperator state file: {e}")

def get_auth_headers() -> Dict[str, str]:
    """Retrieve auth headers using the verified x-api-key scheme."""
    auth_key = os.getenv("MYOPERATOR_AUTH_KEY")
    if not auth_key:
        raise ValueError("MYOPERATOR_AUTH_KEY is not defined in the environment.")
    return {"x-api-key": auth_key}

def fetch_call_logs(from_ts: int, to_ts: int, log_from: int = 0, limit: int = 100) -> Dict[str, Any]:
    """Fetch call logs from MyOperator server-side filtered by timestamp range and paginated."""
    url = "https://developers.myoperator.co/search"
    headers = get_auth_headers()
    payload = {
        "from": from_ts,
        "to": to_ts,
        "log_from": log_from,
        "limit": limit
    }
    
    # Throttle requests to stay well within 20 requests/minute limit
    time.sleep(3.0)
    
    response = requests.post(url, headers=headers, data=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def get_recording_download_url(filename: str) -> str:
    """Get temporary download URL for a call recording file using x-api-key header."""
    url = f"https://developers.myoperator.co/recordings/link?file={filename}"
    headers = get_auth_headers()
    
    time.sleep(3.0) # Throttling
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    res_data = response.json()
    if res_data.get("status") == "success" and "url" in res_data:
        return res_data["url"]
        
    raise ValueError(f"Failed to retrieve link for file {filename}: {res_data.get('message', 'Unknown error')}")

def download_audio_file(download_url: str) -> str:
    """Download audio content from S3 URL and save to standard local uploads directory."""
    file_uuid = str(uuid.uuid4())
    filename = f"{file_uuid}.mp3"
    dest_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Download in chunks
    response = requests.get(download_url, stream=True, timeout=60)
    response.raise_for_status()
    
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    return dest_path

def sync_recent_calls(db: Session, background_tasks: BackgroundTasks, transcribe_task_fn) -> Dict[str, Any]:
    """Orchestrate fetching, downloading, and queueing Whisper transcription for new calls."""
    from_ts = get_last_sync_timestamp()
    to_ts = int(time.time())
    
    logger.info(f"Starting MyOperator Sync | range: {from_ts} -> {to_ts}")
    
    page = 0
    limit = 100
    synced_count = 0
    failed_count = 0
    completed_listing = True
    
    while True:
        offset = page * limit
        logger.info(f"Fetching call logs page {page} (offset {offset})...")
        
        try:
            logs_res = fetch_call_logs(from_ts, to_ts, log_from=offset, limit=limit)
        except Exception as e:
            logger.error(f"Failed to fetch call logs page {page}: {e}")
            completed_listing = False
            break
            
        if logs_res.get("status") != "success":
            logger.error(f"MyOperator logs error response: {logs_res.get('message')}")
            completed_listing = False
            break
            
        hits = logs_res.get("data", {}).get("hits", [])
        if not hits:
            logger.info("No more call logs returned from API.")
            break
            
        for hit in hits:
            source = hit.get("_source", {})
            filename = source.get("filename")
            start_time = source.get("start_time")
            caller_number = source.get("caller_number", "Unknown")
            log_details = source.get("log_details", [])
            agent_name = log_details[0]["received_by"][0]["name"] if log_details and log_details[0].get("received_by") else None
            call_direction = "inbound" if source.get("type") == 1 else "outbound"
            
            # NOTE: Do NOT use the 'seconds' field from the MyOperator response (e.g. source.get("seconds"))
            # to determine call duration, as it does not match end_time - start_time or the formatted duration.
            # It appears to be an unrelated metric and should be ignored. Actual duration is calculated post-transcription.
            
            if not filename:
                continue
                
            # Verify if recording already exists in DB to avoid duplicate syncs
            existing = db.query(AudioFile).filter(AudioFile.filename == filename).first()
            if existing:
                continue
                
            logger.info(f"Syncing new recording: {filename} from {caller_number}")
            
            try:
                # 1. Fetch Temporary Link
                download_url = get_recording_download_url(filename)
                
                # 2. Download File physically
                local_path = download_audio_file(download_url)
                file_size = os.path.getsize(local_path)
                
                # 3. Save DB Record using call start time as created_at
                db_file = AudioFile(
                    filename=filename, # Keep original filename to track duplicates
                    file_path=local_path,
                    file_size=file_size,
                    mime_type="audio/mpeg",
                    caller_number=caller_number,
                    agent_name=agent_name,
                    call_direction=call_direction,
                    status="pending",
                    created_at=datetime.datetime.utcfromtimestamp(start_time) # original call start time
                )
                db.add(db_file)
                db.commit()
                db.refresh(db_file)
                
                # 4. Enqueue Whisper Transcription background task
                background_tasks.add_task(
                    transcribe_task_fn,
                    file_id=db_file.id
                )
                synced_count += 1
                
            except Exception as exc:
                logger.error(f"Failed to sync call log {filename}: {exc}")
                failed_count += 1
                continue
            
        # Move to next page
        page += 1
        
    # Advance the watermark only after the complete source listing was read.
    # A failed page must be retried next run; otherwise those calls are lost.
    if completed_listing:
        save_last_sync_timestamp(to_ts)
    else:
        logger.warning("MyOperator sync did not complete; preserving the previous sync watermark.")
    
    return {
        "status": "success",
        "synced_count": synced_count,
        "failed_count": failed_count,
        "range_start": from_ts,
        "range_end": to_ts,
        "watermark_advanced": completed_listing
    }
