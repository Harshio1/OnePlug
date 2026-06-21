import os, time
from faster_whisper import WhisperModel

os.environ["TQDM_DISABLE"] = "1"
AUDIO = r"uploads\294023a7-65bb-4c1c-ab22-d88d0359cabe.mp3"

print("Loading large-v3...")
model = WhisperModel("large-v3", device="cpu", compute_type="int8", download_root="model_cache")

print("Transcribing (task=transcribe)...")
segments, info = model.transcribe(
    AUDIO,
    task="transcribe",
    language="ta",
    beam_size=5,
    temperature=0,
    vad_filter=False,
    condition_on_previous_text=False
)

print(f"Detected: {info.language} (p={info.language_probability:.3f})")
for seg in segments:
    print(f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
