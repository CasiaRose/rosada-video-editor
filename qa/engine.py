#!/usr/bin/env python3
"""Configurable technical checks.

Default checks are generic: loudness and true peak against the targets in the
style profile, audio/video duration, black frames, frozen or repeated frames,
captions inside the safe zone, and overlapping text boxes.

Any other check stays off until the checks file enables it. A check that is
enabled but cannot run is "not_run". The cut is deliverable only when every
enabled check passed. Disabled checks are omitted.
"""
import argparse, json, os, subprocess, sys
import numpy as np

DEFAULT_CHECKS = {
    "loudness": {"enabled": True},
    "true_peak": {"enabled": True},
    "av_sync": {"enabled": True, "max_delta_s": 0.08},
    "black_frames": {"enabled": True, "luma_below": 12},
    "frozen_or_repeated": {"enabled": True, "max_ratio": 0.05},
    "caption_safe_zone": {"enabled": True},
    "text_overlap": {"enabled": True},
    "skin_cast": {"enabled": False},
    "orientation": {"enabled": False},
}

def merge_checks(override):
    out = json.loads(json.dumps(DEFAULT_CHECKS))
    if not override:
        return out
    if not isinstance(override, dict):
        raise ValueError("checks config must be a mapping")
    for name, spec in override.items():
        if name not in out:
            raise ValueError(f"unknown check {name!r}")
        if not isinstance(spec, dict):
            raise ValueError(f"check {name} must be a mapping")
        out[name].update(spec)
    return out

def load_checks(path):
    if not path:
        return merge_checks(None)
    data = json.load(open(path, encoding="utf-8"))
    # allow {"checks": {...}} or a bare mapping of check names
    if "checks" in data and isinstance(data["checks"], dict):
        data = data["checks"]
    return merge_checks(data)

def _row(name, status, **detail):
    return {"name": name, "status": status, **detail}

def _boxes_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

def evaluate(measurements, checks=None, style=None):
    """Judge measurements. Missing data for an enabled check is not_run, not a pass."""
    checks = merge_checks(checks)
    audio = (style or {}).get("audio") or {}
    captions = (style or {}).get("captions") or {}
    target = float(audio.get("master_lufs", -14.0))
    window = float(audio.get("lufs_window", 1.0))
    peak_limit = float(audio.get("true_peak_db", -1.0))
    safe_top = int(captions.get("safe_top", 150))
    safe_bottom = int(captions.get("safe_bottom", 320))
    results = []
    meas = measurements or {}

    def enabled(name):
        return bool(checks[name].get("enabled"))

    if enabled("loudness"):
        if "integrated_lufs" not in meas:
            results.append(_row("loudness", "not_run", reason="no integrated loudness measurement"))
        else:
            value = float(meas["integrated_lufs"])
            ok = abs(value - target) <= window
            results.append(_row("loudness", "pass" if ok else "fail", integrated_lufs=value, target=target, window=window))
    if enabled("true_peak"):
        if "true_peak_db" not in meas:
            results.append(_row("true_peak", "not_run", reason="no true-peak measurement"))
        else:
            value = float(meas["true_peak_db"])
            ok = value <= peak_limit
            results.append(_row("true_peak", "pass" if ok else "fail", true_peak_db=value, limit=peak_limit))
    if enabled("av_sync"):
        if "video_s" not in meas or "audio_s" not in meas:
            results.append(_row("av_sync", "not_run", reason="stream durations were not measured"))
        else:
            delta = abs(float(meas["video_s"]) - float(meas["audio_s"]))
            limit = float(checks["av_sync"].get("max_delta_s", 0.08))
            results.append(_row("av_sync", "pass" if delta <= limit else "fail", delta_s=round(delta, 4), max_delta_s=limit))
    if enabled("black_frames"):
        if "min_luma" not in meas:
            results.append(_row("black_frames", "not_run", reason="frames were not sampled"))
        else:
            floor = float(checks["black_frames"].get("luma_below", 12))
            value = float(meas["min_luma"])
            results.append(_row("black_frames", "pass" if value >= floor else "fail", min_luma=value, luma_below=floor))
    if enabled("frozen_or_repeated"):
        if "repeat_ratio" not in meas:
            results.append(_row("frozen_or_repeated", "not_run", reason="frame differences were not sampled"))
        else:
            ratio = float(meas["repeat_ratio"])
            limit = float(checks["frozen_or_repeated"].get("max_ratio", 0.05))
            results.append(_row("frozen_or_repeated", "pass" if ratio <= limit else "fail", repeat_ratio=round(ratio, 4), max_ratio=limit))
    if enabled("caption_safe_zone"):
        boxes = meas.get("caption_boxes")
        if not boxes:
            results.append(_row("caption_safe_zone", "not_run", reason="no caption boxes were provided"))
        else:
            bad = [b for b in boxes if b[1] < safe_top or b[3] > 1920 - safe_bottom]
            results.append(_row("caption_safe_zone", "fail" if bad else "pass", safe_top=safe_top, safe_bottom=safe_bottom, outside=bad))
    if enabled("text_overlap"):
        boxes = meas.get("text_boxes")
        if not boxes:
            results.append(_row("text_overlap", "not_run", reason="no text boxes were provided"))
        else:
            hits = []
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    if _boxes_overlap(a["box"], b["box"]):
                        hits.append([a.get("name"), b.get("name")])
            results.append(_row("text_overlap", "fail" if hits else "pass", overlaps=hits))
    if enabled("skin_cast"):
        if "skin_b_star" not in meas or "skin_b_star_raw" not in meas:
            results.append(_row("skin_cast", "not_run", reason="skin samples were not provided"))
        else:
            delta = float(meas["skin_b_star"]) - float(meas["skin_b_star_raw"])
            limit = float(checks["skin_cast"].get("max_delta", 1.5))
            results.append(_row("skin_cast", "pass" if delta <= limit else "fail", delta=round(delta, 3), max_delta=limit))
    if enabled("orientation"):
        if "direct_mad" not in meas or "flipped_mad" not in meas:
            results.append(_row("orientation", "not_run", reason="orientation samples were not provided"))
        else:
            ok = float(meas["direct_mad"]) + 0.5 < float(meas["flipped_mad"])
            results.append(_row("orientation", "pass" if ok else "fail", direct_mad=meas["direct_mad"], flipped_mad=meas["flipped_mad"]))

    failed = [r["name"] for r in results if r["status"] == "fail"]
    not_run = [r["name"] for r in results if r["status"] == "not_run"]
    deliverable = not failed and not not_run and bool(results)
    if not results:
        deliverable = False
        not_run = ["(no checks enabled)"]
    summary = _summary(deliverable, failed, not_run)
    return {"deliverable": deliverable, "failed": failed, "not_run": not_run, "checks": results, "summary": summary}

def _summary(deliverable, failed, not_run):
    if deliverable:
        return "Deliverable. Every enabled check passed."
    parts = ["Not deliverable."]
    if not_run:
        parts.append("These checks did not run: " + ", ".join(not_run) + ".")
    if failed:
        parts.append("These checks failed: " + ", ".join(failed) + ".")
    return " ".join(parts)

def _sh(args):
    return subprocess.run(args, capture_output=True, text=True)

def measure_media(path):
    """Loudness, durations, and a coarse frame sample. Raises nothing; missing fields stay absent."""
    meas = {}
    try:
        err = _sh(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr.splitlines()
        meas["integrated_lufs"] = float([ln.split()[1] for ln in err if ln.strip().startswith("I:")][-1])
        meas["true_peak_db"] = float([ln.split()[1] for ln in err if ln.strip().startswith("Peak:")][-1])
    except (IndexError, ValueError, subprocess.SubprocessError):
        pass
    try:
        meas["video_s"] = float(_sh(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=duration", "-of", "csv=p=0", path]).stdout.strip().splitlines()[-1])
        meas["audio_s"] = float(_sh(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=duration", "-of", "csv=p=0", path]).stdout.strip().splitlines()[-1])
    except (IndexError, ValueError, subprocess.SubprocessError):
        pass
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=64:114,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
        frame = 64 * 114
        n = len(raw) // frame
        if n:
            gray = np.frombuffer(raw, np.uint8)[:n * frame].reshape(n, 114, 64).astype(np.float32)
            meas["min_luma"] = float(gray.mean(axis=(1, 2)).min())
            if n > 1:
                diff = np.abs(np.diff(gray, axis=0)).mean(axis=(1, 2))
                meas["repeat_ratio"] = float(np.mean(diff < 0.4))
    except (ValueError, subprocess.SubprocessError):
        pass
    return meas

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video", nargs="?")
    ap.add_argument("--checks")
    ap.add_argument("--style")
    ap.add_argument("--layout", help="JSON with caption_boxes and text_boxes")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from style.profile import load_profile, NEUTRAL
    style = load_profile(args.style) if args.style else NEUTRAL
    checks = load_checks(args.checks)
    meas = measure_media(args.video) if args.video else {}
    if args.layout:
        meas.update(json.load(open(args.layout, encoding="utf-8")))
    report = evaluate(meas, checks, style)
    text = json.dumps(report, indent=2)
    print(report["summary"])
    print(text)
    if args.json:
        open(args.json, "w", encoding="utf-8").write(text + "\n")
    return 0 if report["deliverable"] else 1

if __name__ == "__main__":
    sys.exit(main())
