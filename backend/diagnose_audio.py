# -*- coding: utf-8 -*-
"""
OnePlug EV — Full Tamil Audio Diagnostic
=========================================
For every uploaded audio file:
1. Run ffprobe — sample rate, bitrate, channels, duration, codec
2. Load audio as numpy — measure amplitude, silence ratio
3. Run Whisper (small model) with task=translate AND task=transcribe
4. Log every segment: no_speech_prob, avg_logprob, compression_ratio, text
5. Classify failure type
6. Generate a structured report

Run from:  backend/  (where uploads/ is a subdirectory)
"""

import os, sys, io, json, time, subprocess, shutil, traceback
from pathlib import Path
from collections import defaultdict

import numpy as np

# ── Safe console print (Windows cp1252 cannot encode Tamil script) ────
def safe_print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    safe = text.encode("cp1252", errors="replace").decode("cp1252")
    print(safe, **kwargs)

# ── stderr guard (Windows tqdm crash) ─────────────────────────────────
_real_stderr = sys.stderr
sys.stderr = open(os.devnull, "w", encoding="utf-8")

import whisper
import static_ffmpeg
static_ffmpeg.add_paths()

sys.stderr.close()
sys.stderr = _real_stderr

UPLOAD_DIR = Path("uploads")
REPORT_PATH = Path("diagnostic_report.json")
LOG_PATH    = Path("diagnostic_report.txt")

MODELS_TO_TEST = ["small"]          # change to ["tiny","base","small","medium"] for full run
TASKS_TO_TEST  = ["translate", "transcribe"]

FFPROBE = shutil.which("ffprobe") or shutil.which("ffprobe.EXE")

# ── Whisper params (same as production) ───────────────────────────────
WHISPER_PARAMS = {
    "fp16": False,
    "verbose": False,
    "no_speech_threshold": 1.0,
    "compression_ratio_threshold": 5.0,
    "condition_on_previous_text": False,
    "logprob_threshold": None,
}

# ─────────────────────────────────────────────────────────────────────
def ffprobe_info(path: str) -> dict:
    """Return audio stream properties from ffprobe."""
    cmd = [
        FFPROBE, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        str(path)
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        data = json.loads(r.stdout)
        streams = data.get("streams", [])
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        fmt = data.get("format", {})
        return {
            "codec":       audio.get("codec_name", "unknown"),
            "sample_rate": int(audio.get("sample_rate", 0)),
            "channels":    int(audio.get("channels", 0)),
            "channel_layout": audio.get("channel_layout", "unknown"),
            "bit_rate":    int(audio.get("bit_rate", fmt.get("bit_rate", 0))),
            "duration_s":  float(audio.get("duration", fmt.get("duration", 0))),
            "format":      fmt.get("format_name", "unknown"),
            "size_bytes":  int(fmt.get("size", 0)),
        }
    except Exception as e:
        return {"error": str(e)}


def amplitude_info(path: str) -> dict:
    """Decode audio to 16 kHz mono PCM, measure amplitude and silence."""
    try:
        audio = whisper.load_audio(str(path))   # float32 [-1, 1], 16 kHz mono
        total_frames = len(audio)
        max_amp   = float(np.abs(audio).max())
        mean_amp  = float(np.abs(audio).mean())
        rms       = float(np.sqrt((audio ** 2).mean()))
        # silence = frames where |x| < 0.01
        silence_ratio = float((np.abs(audio) < 0.01).mean())
        return {
            "total_frames_16k": total_frames,
            "duration_s_decoded": round(total_frames / 16000, 2),
            "max_amplitude":  round(max_amp, 4),
            "mean_amplitude": round(mean_amp, 4),
            "rms":            round(rms, 4),
            "silence_ratio":  round(silence_ratio, 4),
        }
    except Exception as e:
        return {"error": str(e)}


def run_whisper(model, path: str, task: str) -> dict:
    """Run whisper model on file, return full segment metadata + text."""
    params = dict(WHISPER_PARAMS, task=task)

    _re = sys.stderr
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
    t0 = time.time()
    try:
        result = model.transcribe(str(path), **params)
    except Exception as e:
        sys.stderr.close()
        sys.stderr = _re
        return {"error": str(e), "text": "", "segments": [], "elapsed_s": 0}
    finally:
        try:
            sys.stderr.close()
        except Exception:
            pass
        sys.stderr = _re

    elapsed = round(time.time() - t0, 2)
    text = result.get("text", "").strip()
    segs = result.get("segments", [])

    seg_details = []
    for s in segs:
        seg_details.append({
            "start":          round(s.get("start", 0), 2),
            "end":            round(s.get("end", 0), 2),
            "no_speech_prob": round(s.get("no_speech_prob", 0), 4),
            "avg_logprob":    round(s.get("avg_logprob", 0), 4),
            "compression_ratio": round(s.get("compression_ratio", 0), 4),
            "text":           s.get("text", "").strip()[:120],
        })

    # Aggregate stats across segments
    if segs:
        avg_nsp   = round(sum(s.get("no_speech_prob", 0) for s in segs) / len(segs), 4)
        avg_logp  = round(sum(s.get("avg_logprob", 0) for s in segs) / len(segs), 4)
        avg_cr    = round(sum(s.get("compression_ratio", 0) for s in segs) / len(segs), 4)
        max_nsp   = round(max(s.get("no_speech_prob", 0) for s in segs), 4)
        min_nsp   = round(min(s.get("no_speech_prob", 0) for s in segs), 4)
    else:
        avg_nsp = avg_logp = avg_cr = max_nsp = min_nsp = None

    # Classify result
    status, root_cause = classify(text, segs, result)

    return {
        "task":              task,
        "elapsed_s":         elapsed,
        "detected_language": result.get("language", "unknown"),
        "duration_s":        round(result.get("duration", 0), 2),
        "segment_count":     len(segs),
        "text_length":       len(text),
        "word_count":        len(text.split()) if text else 0,
        "text_preview":      text[:250],
        "avg_no_speech_prob": avg_nsp,
        "max_no_speech_prob": max_nsp,
        "min_no_speech_prob": min_nsp,
        "avg_logprob":        avg_logp,
        "avg_compression_ratio": avg_cr,
        "status":            status,
        "root_cause":        root_cause,
        "segments":          seg_details,
    }


def classify(text: str, segs: list, result: dict) -> tuple:
    """Return (status, root_cause) based on whisper output."""
    text = text.strip()
    duration = result.get("duration", 0)

    if not text:
        if not segs:
            return "FAIL", "zero_segments_no_speech_detected"
        return "FAIL", "segments_present_but_no_text"

    if len(text) < 20:
        return "FAIL", "transcript_too_short_likely_noise"

    # Check if output is pure hallucination (model output = prompt text)
    hallucinations = [
        "this audio may be in tamil",
        "oneplug ev",
        "music",
        "thank you for watching",
        "subscribe",
    ]
    low = text.lower()
    for h in hallucinations:
        if low.startswith(h):
            return "FAIL", f"hallucination_detected ({h!r})"

    # High no_speech all segs
    if segs and all(s.get("no_speech_prob", 0) > 0.8 for s in segs):
        return "PARTIAL", "high_no_speech_prob_all_segments_gt_0.8"

    if len(text) > 50:
        return "PASS", "ok"

    return "PARTIAL", "short_transcript_possible_partial"


# ─────────────────────────────────────────────────────────────────────
def main():
    files = sorted(UPLOAD_DIR.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    # Deduplicate by size (same file uploaded multiple times)
    seen_sizes = {}
    unique_files = []
    for f in files:
        sz = f.stat().st_size
        if sz not in seen_sizes:
            seen_sizes[sz] = f
            unique_files.append(f)

    print(f"Found {len(files)} total files, {len(unique_files)} unique by size", flush=True)
    print(f"Models: {MODELS_TO_TEST}  Tasks: {TASKS_TO_TEST}", flush=True)
    print("=" * 72, flush=True)

    # Load models once
    loaded_models = {}
    for mname in MODELS_TO_TEST:
        print(f"Loading model '{mname}'...", flush=True)
        _re = sys.stderr
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
        try:
            loaded_models[mname] = whisper.load_model(mname, device="cpu")
        finally:
            try: sys.stderr.close()
            except: pass
            sys.stderr = _re
        print(f"  '{mname}' loaded OK", flush=True)

    all_results = []

    for idx, fpath in enumerate(unique_files):
        print(f"\n[{idx+1}/{len(unique_files)}] {fpath.name}  ({fpath.stat().st_size//1024} KB)", flush=True)

        file_result = {
            "file": fpath.name,
            "size_kb": round(fpath.stat().st_size / 1024, 1),
            "ffprobe": ffprobe_info(str(fpath)),
            "amplitude": amplitude_info(str(fpath)),
            "whisper_runs": [],
        }

        ff = file_result["ffprobe"]
        amp = file_result["amplitude"]
        safe_print(f"  ffprobe: codec={ff.get('codec')} sr={ff.get('sample_rate')} ch={ff.get('channels')} "
              f"br={ff.get('bit_rate',0)//1000}kbps dur={ff.get('duration_s',0):.1f}s", flush=True)
        safe_print(f"  amplitude: max={amp.get('max_amplitude','?')} rms={amp.get('rms','?')} "
              f"silence={amp.get('silence_ratio','?')}", flush=True)

        for mname, model in loaded_models.items():
            for task in TASKS_TO_TEST:
                safe_print(f"  Running {mname}/{task}...", end=" ", flush=True)
                r = run_whisper(model, str(fpath), task)
                r["model"] = mname
                file_result["whisper_runs"].append(r)
                status_str = r["status"]
                safe_print(f"{status_str} | lang={r['detected_language']} segs={r['segment_count']} "
                      f"words={r['word_count']} nsp={r['avg_no_speech_prob']} logp={r['avg_logprob']} "
                      f"[{r['elapsed_s']}s]", flush=True)
                if r["text_preview"]:
                    safe_print(f"    TEXT: {r['text_preview'][:120]}", flush=True)
                if r.get("root_cause") and r["status"] != "PASS":
                    safe_print(f"    ROOT CAUSE: {r['root_cause']}", flush=True)

        all_results.append(file_result)

    # ── Write JSON report ──────────────────────────────────────────────
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report saved: {REPORT_PATH}", flush=True)

    # ── Write human-readable summary ──────────────────────────────────
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        pass_files    = []
        partial_files = []
        fail_files    = []

        for r in all_results:
            # Use translate/small as primary verdict
            primary = next(
                (run for run in r["whisper_runs"] if run["model"] == "small" and run["task"] == "translate"),
                r["whisper_runs"][0] if r["whisper_runs"] else None
            )
            if not primary:
                continue
            entry = (r["file"], r["size_kb"], r["ffprobe"], r["amplitude"], primary)
            if primary["status"] == "PASS":
                pass_files.append(entry)
            elif primary["status"] == "PARTIAL":
                partial_files.append(entry)
            else:
                fail_files.append(entry)

        def write_section(title, items):
            with open(LOG_PATH, "a", encoding="utf-8") as fout:
                fout.write(f"\n{'='*72}\n{title} ({len(items)} files)\n{'='*72}\n")
                for (fname, kb, ff, amp, run) in items:
                    fout.write(f"\n  FILE: {fname}  ({kb} KB)\n")
                    fout.write(f"  codec={ff.get('codec')} sr={ff.get('sample_rate')} "
                               f"ch={ff.get('channels')} br={ff.get('bit_rate',0)//1000}kbps "
                               f"dur={ff.get('duration_s',0):.1f}s\n")
                    fout.write(f"  amplitude: max={amp.get('max_amplitude')} rms={amp.get('rms')} "
                               f"silence={amp.get('silence_ratio')}\n")
                    fout.write(f"  Whisper: lang={run['detected_language']} segs={run['segment_count']} "
                               f"words={run['word_count']} nsp_avg={run['avg_no_speech_prob']} "
                               f"logp_avg={run['avg_logprob']}\n")
                    fout.write(f"  Status: {run['status']}  Root cause: {run['root_cause']}\n")
                    if run["text_preview"]:
                        fout.write(f"  Text: {run['text_preview'][:200]}\n")

        write_section("PASSING FILES", pass_files)
        write_section("PARTIAL FILES", partial_files)
        write_section("FAILING FILES", fail_files)

        # Summary table to console
        safe_print("\n" + "=" * 72)
        safe_print(f"SUMMARY: {len(pass_files)} PASS | {len(partial_files)} PARTIAL | {len(fail_files)} FAIL")
        safe_print("=" * 72)

        # Root cause frequency
        root_causes = defaultdict(int)
        for r in all_results:
            for run in r["whisper_runs"]:
                if run["status"] != "PASS":
                    root_causes[run["root_cause"]] += 1
        if root_causes:
            safe_print("\nFailure root cause frequency:")
            for cause, count in sorted(root_causes.items(), key=lambda x: -x[1]):
                safe_print(f"  {count:>3}x  {cause}")

        # Correlation analysis
        safe_print("\nCorrelation analysis (translate/small, FAIL files):")
        for r in all_results:
            primary = next(
                (run for run in r["whisper_runs"] if run["model"] == "small" and run["task"] == "translate"),
                None
            )
            if primary and primary["status"] == "FAIL":
                ff = r["ffprobe"]
                amp = r["amplitude"]
                safe_print(f"  {r['file'][:40]:40s}  sr={ff.get('sample_rate',0):>6}  "
                      f"ch={ff.get('channels',0)}  dur={ff.get('duration_s',0):>5.1f}s  "
                      f"rms={amp.get('rms','?'):>6}  sil={amp.get('silence_ratio','?'):>5}  "
                      f"cause={primary['root_cause']}")

    safe_print(f"\nDetailed log saved: {LOG_PATH}")


if __name__ == "__main__":
    main()
