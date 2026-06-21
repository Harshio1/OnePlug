"""
Quick test: faster-whisper large-v3 on the real Tamil EV support call.
Compare output quality against the small model's known output.
"""
import os, sys, time

os.environ["TQDM_DISABLE"] = "1"

AUDIO = r"uploads\bb6a3a64-1c1f-4251-97a3-ff3c4ff5cf7a.mp3"

from faster_whisper import WhisperModel

print("Loading large-v3 INT8...", flush=True)
t0 = time.time()
model = WhisperModel(
    "large-v3",
    device="cpu",
    compute_type="int8",
    download_root="model_cache"
)
print(f"Loaded in {time.time()-t0:.1f}s", flush=True)

print("Transcribing...", flush=True)
t0 = time.time()
segments_iter, info = model.transcribe(
    AUDIO,
    task="translate",
    beam_size=5,
    best_of=5,
    temperature=0,
    vad_filter=False,
    condition_on_previous_text=False,
)

print(f"Language: {info.language} (p={info.language_probability:.3f})  Duration: {info.duration:.1f}s", flush=True)
print("Consuming segments...", flush=True)

parts = []
for seg in segments_iter:
    text = seg.text.strip()
    parts.append(text)
    print(f"  [{seg.start:.0f}s] nsp={seg.no_speech_prob:.3f} logp={seg.avg_logprob:.3f}  {repr(text[:80])}", flush=True)

elapsed = time.time() - t0
full = " ".join(parts)
print(f"\nDone in {elapsed:.1f}s | {len(parts)} segments | {len(full.split())} words", flush=True)
print("\n=== FULL TRANSCRIPT ===")
print(full)
