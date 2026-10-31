"""Mix helpers: load audio, resolve a bed path, place effects from a cue map.

Levels start at the neutral preset and are replaced from the style profile
before a finish. There is no bundled song library.
"""
import json, os, subprocess, numpy as np
from paths import ROOT, sfx_dir, music_dir
KIT = ROOT; SR = 48000
VO_LUFS, BED_UNDER_DB, GAP_LIFT_DB, SFX_BUS_DB = -16.0, 16.0, 4.0, 1.5
_SFX = None

def apply_audio(audio):
    """Copy master targets from a style profile's audio section."""
    global VO_LUFS, BED_UNDER_DB, GAP_LIFT_DB
    if not audio:
        return
    VO_LUFS = float(audio.get("voice_lufs", VO_LUFS))
    BED_UNDER_DB = float(audio.get("bed_under_db", BED_UNDER_DB))
    GAP_LIFT_DB = float(audio.get("gap_lift_db", GAP_LIFT_DB))

def set_sfx_dir(path):
    global _SFX
    _SFX = path
def load(p, ch=1, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss else []) + ["-i", p] + (["-t", str(t)] if t else []) + ["-vn", "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, ch).astype(np.float64)
def lufs(x):
    x = x if x.ndim == 2 else np.repeat(x[:, None], 2, 1)
    p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f64le", "-ar", str(SR), "-ac", str(x.shape[1]), "-i", "-", "-af", "ebur128", "-f", "null", "-"], input=x.tobytes(), capture_output=True)
    t = p.stderr.decode(); i = t.rfind("I:"); return float(t[i + 2:].split("LUFS")[0])
def song_path(name):
    """Resolve a bed file. Pass a path, or a filename inside VEDIT_MUSIC."""
    if not name:
        raise FileNotFoundError("no music bed; generate one or pass a file path")
    if os.path.exists(name):
        return os.path.abspath(name)
    candidate = os.path.join(music_dir(), name)
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f"music bed not found: {name}")
def song_track(name, L, offset=0.0):
    """Song as stereo array of length L, starting `offset` s into the song; loops with a 1 s crossfade if too short."""
    m = load(song_path(name), 2)[int(offset * SR):]; xf = SR
    while len(m) < L:
        r = np.linspace(0, 1, xf)[:, None]; base = load(song_path(name), 2)
        m = np.concatenate([m[:-xf], m[-xf:] * (1 - r) + base[:xf] * r, base[xf:]])
    return m[:L]
def cue_map():
    path = os.path.join(_SFX or sfx_dir(), "cue_map.json")
    if not os.path.exists(path):
        return {}
    return json.load(open(path))
def expand_cues(cues):
    """-> list of dict(t, event, file, db, start_sample, wave). Unknown events are skipped."""
    M = cue_map()
    if not M or not cues:
        return []
    out = []
    for c in cues:
        if c["event"] == "type_run":
            s = c.get("text", ""); tf = c.get("type_frames", 18)
            for k in range(0, len(s), 3): out.append({"t": c["t"] + (3 + k * tf / len(s)) / 30, "event": "type_tick"})
        else: out.append(dict(c))
    res, kept = [], []
    pri = {"riser_hit": 0, "whoosh": 1, "pop": 2, "glitch_cut": 0, "punch_in_big": 1, "punch_in_small": 1, "panel_in": 2, "panel_out": 2}
    for c in sorted(out, key=lambda c: (pri.get(c["event"], 3), c["t"])):   # no stacking within 120 ms (type ticks exempt among themselves)
        if any(abs(k["t"] - c["t"]) < 0.12 and not (k["event"] == c["event"] == "type_tick") for k in kept): continue
        kept.append(c)
    for c in sorted(kept, key=lambda c: c["t"]):
        aliases = {"broll_in": "transition", "broll_out": "transition", "glitch_cut": "transition", "panel_in": "transition",
                   "panel_out": "transition", "whoosh": "transition", "pop": "text", "punch_in_big": "text", "punch_in_small": "text", "type_tick": "text"}
        key = c["event"] if c["event"] in M else aliases.get(c["event"])
        if key not in M:
            key = "cut" if "cut" in M else None
        if not key:
            continue
        m = M[key]; w = load(os.path.join(_SFX or sfx_dir(), m["file"]))[:, 0]; db = c.get("db", m["db"])
        w = w / max(1e-6, np.abs(w).max()) * 0.5 * 10 ** (db / 20) * 10 ** (SFX_BUS_DB / 20)
        t = c["t"] + m.get("offset_s", 0); st = int(round(t * SR)) - (int(np.argmax(np.abs(w))) if m["align"] == "peak" else 0)
        res.append(dict(t=round(c["t"], 3), event=c["event"], file=m["file"], db=db, start_sample=max(0, st), wave=w[max(0, -st):]))
    return res
def speech_activity(vo, hop=960):
    L = len(vo); edb = 20 * np.log10(np.array([np.sqrt(np.mean(vo[i:i + hop] ** 2) + 1e-12) for i in range(0, L, hop)]))
    act = edb > (np.percentile(edb, 90) - 22); a = act.copy()
    for i in range(len(a)):
        if act[max(0, i - 3):i + 1].any(): a[i] = True
    k = 0
    while k < len(a):
        if not a[k]:
            j = k
            while j < len(a) and not a[j]: j += 1
            if j - k < 7 and k > 0 and j < len(a): a[k:j] = True
            k = j
        else: k += 1
    return a
