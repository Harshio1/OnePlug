"""
Backfill caller_number, agent_name, and call_direction for existing audio_files rows.
"""
import sys
import os
import time
sys.path.insert(0, '/var/www/oneplug/backend')

from dotenv import load_dotenv
load_dotenv('/var/www/oneplug/backend/.env')

from app.db import SessionLocal
from app.models import AudioFile
from app.integrations.myoperator import fetch_call_logs

def backfill():
    db = SessionLocal()
    page = 0
    limit = 20
    updated = 0
    skipped = 0
    not_found = 0

    from_ts = 1781520361
    to_ts = 1782926723

    print(f"Starting backfill | from_ts={from_ts} to_ts={to_ts}")

    while True:
        offset = page * limit
        print(f"Fetching page {page} (offset {offset})...")

        try:
            logs_res = fetch_call_logs(from_ts, to_ts, log_from=offset, limit=limit)
        except Exception as e:
            print(f"Failed to fetch page {page}: {e}")
            break

        if logs_res.get("status") != "success":
            print(f"API error: {logs_res.get('message')}")
            break

        hits = logs_res.get("data", {}).get("hits", [])
        if not hits:
            print("No more hits.")
            break

        for hit in hits:
            source = hit.get("_source", {})
            filename = source.get("filename")
            caller_number = source.get("caller_number", "Unknown")
            log_details = source.get("log_details", [])
            agent_name = log_details[0]["received_by"][0]["name"] if log_details and log_details[0].get("received_by") else None
            call_direction = "inbound" if source.get("event") == 1 else "outbound"

            if not filename:
                continue

            existing = db.query(AudioFile).filter(AudioFile.filename == filename).first()
            if not existing:
                not_found += 1
                continue

            direction_changed = existing.call_direction != call_direction
            if existing.caller_number and existing.agent_name and not direction_changed:
                skipped += 1
                continue

            existing.caller_number = existing.caller_number or caller_number
            existing.agent_name = existing.agent_name or agent_name
            existing.call_direction = call_direction
            db.commit()
            updated += 1
            print(f"Updated: {caller_number} | {agent_name} | {call_direction}")

        page += 1
        time.sleep(0.3)

    db.close()
    print(f"\nDone. Updated={updated} | Skipped={skipped} | Not in DB={not_found}")

if __name__ == "__main__":
    backfill()
