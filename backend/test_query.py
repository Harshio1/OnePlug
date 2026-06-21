import sys
import os
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.services import db_service

def main():
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        two_days_ago = now - datetime.timedelta(days=2)
        print("utcnow:", now)
        print("two_days_ago:", two_days_ago)

        files = db_service.get_audio_files(db)
        print("Total files returned by get_audio_files:", len(files))
        if files:
            print("Newest file date:", files[0].created_at)
            print("Oldest file date:", files[-1].created_at)

    finally:
        db.close()

if __name__ == "__main__":
    main()
