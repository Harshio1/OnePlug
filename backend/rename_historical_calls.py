import sqlite3
import json
import os

DB_PATH = "oneplug_fallback.db"

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find all completed transcripts
    cursor.execute("""
        SELECT a.id, a.filename, t.analysis 
        FROM audio_files a
        JOIN transcripts t ON a.id = t.audio_file_id
        WHERE a.status = 'completed'
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} completed calls to potentially rename.")

    updated_count = 0
    for file_id, current_filename, analysis_json in rows:
        if not analysis_json:
            continue
            
        try:
            analysis = json.loads(analysis_json)
        except Exception:
            try:
                # Fallback if double encoded or stored as string evaluation
                analysis = eval(analysis_json)
            except Exception:
                continue

        desc_text = analysis.get("main_concern") or analysis.get("summary")
        if not desc_text or "AI Analysis fallback" in desc_text:
            continue

        # Generate a short 2-3 word description
        words = [w.strip(".,?!();:\"'") for w in desc_text.split() if w.strip()]
        short_desc = " ".join(words[:3]) # Take first 3 words
        
        if short_desc:
            ext = os.path.splitext(current_filename)[1] or ".mp3"
            new_filename = f"{short_desc}{ext}"
            
            cursor.execute("UPDATE audio_files SET filename = ? WHERE id = ?", (new_filename, file_id))
            print(f"Renamed: '{current_filename}' -> '{new_filename}'")
            updated_count += 1

    conn.commit()
    conn.close()
    print(f"\nMigration complete. Successfully renamed {updated_count} calls.")

if __name__ == "__main__":
    main()
