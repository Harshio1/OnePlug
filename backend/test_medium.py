"""
Test medium model vs small model on the latest uploaded audio.
Shows side-by-side accuracy comparison for proper nouns and numbers.
"""
import os, sys, io, time

os.environ["TQDM_DISABLE"] = "1"

AUDIO = r"uploads\bb6a3a64-1c1f-4251-97a3-ff3c4ff5cf7a.mp3"

class NullIO(io.IOBase):
    def write(self, *a): return 0
    def flush(self): pass
    def writable(self): return True

def run(model, label):
    params = dict(
        task="translate", fp16=False, verbose=False,
        no_speech_threshold=1.0, compression_ratio_threshold=5.0,
        condition_on_previous_text=False, logprob_threshold=None,
    )
    _re = sys.stderr; sys.stderr = NullIO()
    t0 = time.time()
    try:
        result = model.transcribe(AUDIO, **params)
    finally:
        sys.stderr = _re
    elapsed = time.time() - t0
    text = result.get("text","").strip()
    segs = result.get("segments",[])
    print(f"\n{'='*60}")
    print(f"MODEL: {label}  |  {elapsed:.0f}s  |  {len(text.split())} words  |  {len(segs)} segments")
    print(f"{'='*60}")
    print(text)
    print()
    print("Per-segment stats:")
    for s in segs:
        print(f"  [{s['start']:.0f}s] nsp={s.get('no_speech_prob',0):.3f} logp={s.get('avg_logprob',0):.3f}  {repr(s['text'][:80])}")

import whisper, torch
print("Loading small model...")
_re = sys.stderr; sys.stderr = NullIO()
small = whisper.load_model("small", device="cpu")
sys.stderr = _re
print("small loaded. Testing...")
run(small, "small")
del small

print("\nLoading medium model...")
_re = sys.stderr; sys.stderr = NullIO()
medium = whisper.load_model("medium", device="cpu")
sys.stderr = _re
print("medium loaded. Testing...")
run(medium, "medium")
del medium
