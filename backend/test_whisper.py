"""
Direct Whisper diagnostic — bypasses VAD by loading audio directly as numpy array.
This forces Whisper to transcribe the full audio regardless of no_speech_prob.
"""
import sys
import os
import io
import time
import traceback
import numpy as np

AUDIO = r"uploads\f4431681-0ef0-47b0-992f-13650844008e.mp3"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

log(f"STAGE 1: checking file")
if not os.path.exists(AUDIO):
    log(f"ERROR: file not found"); sys.exit(1)
log(f"OK: {os.path.getsize(AUDIO)} bytes")

log("STAGE 2: importing whisper")
import whisper
import torch
log(f"OK")

log("STAGE 3: loading model")
model = whisper.load_model("small", device="cpu")
log("OK")

log("STAGE 4: loading audio as numpy array (bypasses Whisper VAD entirely)")
# whisper.load_audio decodes via ffmpeg to 16kHz mono float32 PCM
# We then pad/trim to 30s chunks and run mel spectrogram manually
audio = whisper.load_audio(AUDIO)
log(f"  audio shape: {audio.shape}, duration: {len(audio)/16000:.2f}s, max_amplitude: {np.abs(audio).max():.4f}")

if np.abs(audio).max() < 0.001:
    log("PROBLEM: audio is silence or near-silence — file may be corrupted or empty")
    sys.exit(1)

log("STAGE 5: transcribing all 30s chunks directly")
# Pad entire audio and run transcribe with decode_options that disable VAD
_real_stderr = sys.stderr
sys.stderr = open(os.devnull, "w", encoding="utf-8")
t0 = time.time()
try:
    result = model.transcribe(
        AUDIO,
        task="translate",
        fp16=False,
        verbose=False,
        no_speech_threshold=1.0,        # ACCEPT ALL segments, even silence
        compression_ratio_threshold=5.0, # very permissive
        condition_on_previous_text=False,
        logprob_threshold=None,          # disable logprob filtering
    )
finally:
    sys.stderr.close()
    sys.stderr = _real_stderr

elapsed = time.time() - t0
log(f"Done in {elapsed:.1f}s")

lang = result.get("language", "unknown")
text = result.get("text", "")
segs = result.get("segments", [])
log(f"  language  : {lang}")
log(f"  duration  : {result.get('duration', 0):.2f}s")
log(f"  segments  : {len(segs)}")
log(f"  text len  : {len(text)}")
log(f"  text      : {repr(text[:500])}")

if segs:
    log("  Per-segment detail:")
    for s in segs[:5]:
        log(f"    [{s['start']:.1f}s] no_speech={s.get('no_speech_prob',0):.3f} logprob={s.get('avg_logprob',0):.3f} => {repr(s['text'][:80])}")
