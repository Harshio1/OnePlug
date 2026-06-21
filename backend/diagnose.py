import sys
import os

# Force UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import static_ffmpeg
import whisper

static_ffmpeg.add_paths()

# Pick the most recent upload
upload_dir = "uploads"
files = sorted(
    os.listdir(upload_dir),
    key=lambda f: os.path.getmtime(os.path.join(upload_dir, f)),
    reverse=True
)
if not files:
    print("No files in uploads/")
    exit(1)

audio_file = os.path.join(upload_dir, files[0])
print(f"File: {audio_file}  ({os.path.getsize(audio_file)/1024:.1f} KB)")

model = whisper.load_model("medium")
print("Model ready. Transcribing with language=en (Tanglish output)...")

result = model.transcribe(
    audio_file,
    language="en",          # force English -> Tanglish phonetic output
    fp16=False,
    task="transcribe",
    verbose=None,           # suppress internal prints (avoids cp1252 crash)
    no_speech_threshold=0.3,
    compression_ratio_threshold=2.8,
    condition_on_previous_text=False,
    word_timestamps=False,
)

segs = result.get("segments", [])
text = result.get("text", "")

print()
print("=" * 60)
print(f"Duration   : {result.get('duration', 0):.2f}s")
print(f"Segments   : {len(segs)}")
print(f"Words      : {len(text.split())}")
print("=" * 60)
for s in segs:
    print(f"[{s['start']:6.2f}s -> {s['end']:6.2f}s]  {s['text'].strip()}")
print()
print("FULL TEXT:")
print(text)
