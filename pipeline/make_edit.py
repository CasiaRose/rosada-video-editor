#!/usr/bin/env python3
"""Build one edit from a recipe and a style profile.
  pipeline/make_edit.sh recipe.json
recipe.json paths are relative to the recipe. See examples/recipe.example.json.
The style profile (recipe "style", or style/presets/plain.yaml) sets pace, captions,
border, and sound. A missing bed is generated into the project cache.
Exit code 1 means the configurable checks are not deliverable."""
import sys, os, json, subprocess, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import ROOT, hotwords, agents as env_agents
from style.profile import load_profile
from sound.generate import generate as generate_sound
KIT = ROOT; B = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, B); import edit_policy as RR, smooth_clip as SC
rp = os.path.abspath(sys.argv[1]); R = json.load(open(rp)); D = os.path.dirname(rp); os.chdir(D)
BD = os.path.join(D, "build"); os.makedirs(BD, exist_ok=True)
def P(p): return p if os.path.isabs(p) else (os.path.join(D, p) if os.path.exists(os.path.join(D, p)) else os.path.join(KIT, p))
style = load_profile(P(R["style"]) if R.get("style") else os.path.join(ROOT, "style", "presets", "plain.yaml"))
RR.apply_style(style)
RR.configure(R.get("names") or R.get("agents") or env_agents())
json.dump(style, open(os.path.join(BD, "style.json"), "w"), indent=2)
def run(*a): print("+", " ".join(map(str, a))[:220], flush=True); subprocess.run(list(map(str, a)), check=True)
def dur_of(f): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
edit = P(R["edit"]); DUR = dur_of(edit); cues = []; overlays = []
# 1) words
words = R.get("words")
if not words:
    words = os.path.join(BD, "words.json")
    from faster_whisper import WhisperModel
    hw = R.get("hotwords") or hotwords() or None
    m = WhisperModel("medium", compute_type="int8"); segs, _ = m.transcribe(edit, language="en", word_timestamps=True, beam_size=5, condition_on_previous_text=False, hotwords=hw)
    json.dump([dict(w=w.word.strip(), s=round(w.start, 3), e=round(w.end, 3)) for s in segs for w in s.words], open(words, "w"))
words = P(words); emph = R.get("emphasis", []); emph_words = ";".join(e.split(":")[0] for e in emph)
hook = R.get("hook"); HD = hook.get("dur", 2.8) if hook else 0
brolls = R.get("broll", []); panels = R.get("panels", [])
def pdict(p):
    d = json.load(open(P(p["params"]))) if isinstance(p.get("params"), str) else dict(p.get("params", {}))
    if "dur" in p: d["dur"] = p["dur"]
    return d
full = [(p["t"], p["t"] + pdict(p).get("dur", 4)) for p in panels if pdict(p).get("pos") == "full"]
WORDS = json.load(open(words)); WORDS = WORDS if isinstance(WORDS, list) else [dict(w=w["word"], s=w["start"], e=w["end"]) for s in WORDS["segments"] for w in s["words"]]
WORDS = [dict(w=w.get("w") or w.get("word"), s=w.get("s", w.get("start")), e=w.get("e", w.get("end"))) for w in WORDS]
problems = []
# --- SHOW-WHAT-YOU-SAY: every pointing phrase / agent name gets footage (auto-inserted from recipe "show" library if missing)
def kind_of(b): return "graphic" if RR.looks_graphic(str(b.get("file", ""))) else b.get("kind", "hq_footage")
def shots_now(): return ([(0, HD, kind_of(hook["broll"]))] if hook and hook.get("broll") else []) + [(b["t"], b["t"] + b["dur"], kind_of(b)) for b in brolls] + [(a, b, "panel") for a, b in full]
lib = R.get("show", {})
for tr in RR.triggers(WORDS):
    if RR.covered(tr, shots_now()): continue
    name = next((a for a in RR.AGENTS if a.lower() in tr["text"].lower()), None); src = lib.get(name) or lib.get("default")
    if src and tr["needs"] == "hq" and kind_of(src) != "hq_footage":
        problems.append(f"SHOW-WHAT-YOU-SAY: 'show' entry for '{name or 'default'}' ({src.get('file')}) is a graphic/agent card. '{tr['text']}' needs REAL HQ footage of the agent (e.g. Delivery Lab clips)."); continue
    if src:
        t0 = round(max(0, tr["s"] - 0.1), 3); end = max(t0 + 2.0, tr["e"] + 0.3)
        se = next((w["e"] for w in WORDS if w["s"] >= tr["e"] - 0.01 and w["w"][-1:] in ".?!"), None)     # run to the end of the sentence
        if se is not None and se - tr["e"] < 2.5: end = max(end, se + 0.3)
        _jj = R["joins"] if isinstance(R.get("joins"), list) else (json.load(open(P(R["joins"]))) if R.get("joins") else [])
        for j in sorted(_jj):                                                                                  # and swallow a face join right after it
            if end - 0.05 < j < end + RR.MIN_FACE_SHOT: end = j + 0.6
        d = round(min(end, DUR) - t0, 3)
        brolls.append(dict(t=t0, dur=d, **{k: v for k, v in src.items() if k != "label"}, **({"label": src["label"]} if src.get("label") else {})))
        print(f"show-what-you-say: auto B-roll {t0:.2f}-{t0+d:.2f}s for '{tr['text']}'")
    else: problems.append(f"SHOW-WHAT-YOU-SAY: '{tr['text']}' at {tr['s']:.2f}-{tr['e']:.2f}s has no B-roll/screen footage. Add a broll entry starting {tr['s']-0.1:.2f}s lasting to >= {tr['e']:.2f}s, or a 'show' library in the recipe.")
brolls.sort(key=lambda b: b["t"])
# --- CUT RULES: face joins (from cut_vo.py joins.json, recipe "joins", or detected in the edit)
if R.get("joins") is not None: joins = R["joins"] if isinstance(R["joins"], list) else json.load(open(P(R["joins"])))
else:
    _g = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", edit, "-vf", "scale=90:160", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout, np.uint8).reshape(-1, 160, 90).astype(np.float32)
    _d = np.abs(np.diff(_g, axis=0)).mean((1, 2)); joins = [round((i + 1) / 30, 3) for i in np.where(_d > 12)[0]]
cover = shots_now()
face_joins = [j for j in joins if not any(a - 0.05 <= j <= b + 0.05 for a, b, *_ in cover)]
for j in face_joins:
    w = RR.in_word(WORDS, j)
    if w: problems.append(f"CUT RULE: face jump cut at {j:.2f}s lands mid-word '{w['w']}' ({w['s']:.2f}-{w['e']:.2f}). Re-cut with pipeline/cut_vo.py (snaps to silence) or cover it with B-roll.")
events = sorted(face_joins + [b for a, b, *_ in cover if b < DUR - 0.1])      # face cuts + returns-to-face
for x, y in zip(events, events[1:]):
    if y - x < RR.MIN_FACE_SHOT and (x in face_joins or y in face_joins):
        problems.append(f"CUT RULE: face shot {x:.2f}-{y:.2f}s is {y-x:.2f}s (< {RR.MIN_FACE_SHOT}s, back-to-back jump cuts). Cover the join at {y if y in face_joins else x:.2f}s with B-roll, or merge the keeps.")
if problems:
    print("\nmake_edit: recipe breaks the rules (nothing rendered):\n- " + "\n- ".join(problems)); sys.exit(2)
skip = [(0, HD + 0.2)] + [(b["t"], b["t"] + b["dur"] + 0.2) for b in brolls] + [(a, b + 0.2) for a, b in full]   # starts exact: a held zoom resets UNDER the cover
# 2) punch-ins (face only)
json.dump(face_joins, open(os.path.join(BD, "face_joins.json"), "w"))
pi = os.path.join(BD, "1_punch.mp4"); sk = ",".join(f"{max(0,a):.2f}-{b:.2f}" for a, b in skip)
if isinstance(R.get("punchins", "auto"), list):
    json.dump(R["punchins"], open(os.path.join(BD, "punch_cues.json"), "w")); run("python3", f"{B}/punchins.py", edit, pi, "--cues", os.path.join(BD, "punch_cues.json"), "--skip", sk, "--joins", os.path.join(BD, "face_joins.json"))
else: run("python3", f"{B}/punchins.py", edit, pi, "--words", words, "--emphasis", emph_words, "--skip", sk, "--joins", os.path.join(BD, "face_joins.json"), *(["--anchor", R["anchor"]] if R.get("anchor") else []))
cues += json.load(open(pi + ".punchins.json"))["cues"]
# 3) B-roll (hook B-roll at 0 + inserts, incl. auto show-what-you-say inserts)
segs = ([dict(t=0, dur=HD, **hook["broll"])] if hook and hook.get("broll") else []) + brolls
ins, fc, last = ["-i", pi], "", "0:v"
for i, s in enumerate(segs):
    # v3.1 B-roll prep: constant 30 fps, duplicate/VFR frames smoothed away, NO added drift on footage that already moves;
    # a still gets a gentle SUBPIXEL push (3x supersampled zoompan), never an integer-pixel crop drift.
    clip = os.path.join(BD, f"broll{i}.mp4"); slow = s.get("slow", 1.0); src_t = s["dur"] / slow + 0.1
    st = SC.stats(SC.gray(P(s["file"]), s.get("ss", 0) or None, src_t)); fr = SC.probe(P(s["file"]))
    if SC.ok(st, fr) and slow == 1.0:
        run("ffmpeg", "-v", "error", "-y", "-ss", str(s.get("ss", 0)), "-i", P(s["file"]), "-t", str(s["dur"]), "-vf",
            (f"crop={s['crop']}," if s.get("crop") else "") + "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30", "-an", "-c:v", "libx264", "-crf", "16", clip)
        print(f"broll{i}: {os.path.basename(s['file'])} already smooth {st}")
    else:
        SC.smooth(P(s["file"]), clip, s.get("ss", 0), src_t, slow, s.get("crop"))
    cst = SC.stats(SC.gray(clip))
    if cst["still"] or cst["motion"] < 0.15:
        tmpc = clip + ".push.mp4"
        run("ffmpeg", "-v", "error", "-y", "-i", clip, "-vf", f"scale=3240:5760:flags=lanczos,zoompan=z='1+0.04*on/{max(1, round(s['dur'] * 30))}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x1920:fps=30",
            "-an", "-c:v", "libx264", "-crf", "16", tmpc); os.replace(tmpc, clip); print(f"broll{i}: still -> gentle subpixel push")
    ins += ["-i", clip]
    fc += f"[{i+1}:v]fps=30,setpts=PTS-STARTPTS+{s['t']}/TB[b{i}];[{last}][b{i}]overlay=eof_action=pass:enable='between(t,{s['t']},{s['t']+s['dur']})'[o{i}];"
    last = f"o{i}"
    # v3: B-roll in/out = soft whoosh only (no visual glitch; glitches are for section changes, see below)
    if s["t"] > 0.05: cues.append({"t": round(s["t"], 3), "event": "broll_in"})
    if s["t"] + s["dur"] < DUR - 0.1 and not (hook and s is segs[0]): cues.append({"t": round(s["t"] + s["dur"], 3), "event": "broll_out"})
v2 = os.path.join(BD, "2_broll.mp4")
if segs: run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc + f"[{last}]null[vout]", "-map", "[vout]", "-map", "0:a", "-r", "30", "-fps_mode", "cfr", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "copy", "-t", str(DUR), v2)
else: shutil.copy(pi, v2)
# 4) graphics: hook card, B-roll labels, panels -> captured with templates.html, cues from capture
gl = []
if hook: gl.append((0, dict(scene="hook_broll", bg="none", dur=HD, **{k: v for k, v in hook.items() if k not in ("broll", "dur")})))
for b in brolls:
    if b.get("label"): gl.append((b["t"] + 0.15, dict(scene="label", bg="none", dur=min(2.4, b["dur"] - 0.3), **b["label"])))
for p in panels: gl.append((p["t"], pdict(p)))
for k, (t, d) in enumerate(gl):
    pj = os.path.join(BD, f"g{k}_{d['scene']}.json"); json.dump(d, open(pj, "w"))
    out = os.path.join(BD, f"g{k}_{d['scene']}" + (".mp4" if d.get("bg", "none") != "none" else ".mov"))
    run("python3", os.path.join(KIT, "graphics", "capture.py"), pj, out)
    gc = json.load(open(out + ".cues.json"))["cues"]
    cues += [{"t": round(t + c["t"], 3), "event": c["event"]} for c in gc if not c.get("_only_if")]
    overlays.append(dict(file=out, t=t))
    if d["scene"] == "terminal": cues.append({"t": t, "event": "type_run", "text": d.get("text", "")})
    # word-timed pops: spoken words that appear on this graphic while it is up (max 2)
    txt = json.dumps(d).lower(); n = 0
    for w in WORDS:
        core = w["w"].strip(",.?!*").lower()
        if len(core) > 3 and core in txt and t + 0.25 < w["s"] < t + d.get("dur", 3) - 0.2 and n < 2: cues.append({"t": round(w["s"], 3), "event": "pop"}); n += 1
# GLITCHES: section changes only (end of the hook + recipe "sections"), max 1 per 15 s. Never auto-added on cuts.
auto = sorted(set(([round(HD, 3)] if hook else []) + [float(x) for x in R.get("sections", [])]))[:RR.glitch_budget(DUR)]
cues = [c for c in cues if not (c["event"] in ("broll_out",) and any(abs(c["t"] - a) < 0.15 for a in auto))]
cues += [{"t": a, "event": "glitch_cut"} for a in auto] + [{"t": round(a + 0.02, 3), "event": "whoosh"} for a in auto]
print("glitches (section changes only):", auto)
v3 = os.path.join(BD, "3_graphics.mp4")
ins, fc, last = ["-i", v2], "[0:v]null[v_]", "v_"
for i, o in enumerate(overlays):
    ins += ["-itsoffset", str(o["t"]), "-i", o["file"]]
    fc += f";[{last}][{i+1}:v]overlay=0:0:eof_action=pass:enable='between(t,{o['t']},{o['t'] + dur_of(o['file']) - 0.01})'[v{i}]"; last = f"v{i}"
for k, tc in enumerate(auto):
    en = f"enable='between(t,{tc-0.034:.3f},{tc+0.034:.3f})'"; fc += f";[{last}]rgbashift=rh=-14:bh=14:{en},noise=alls=40:allf=t:{en}[a{k}]"; last = f"a{k}"
run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", f"[{last}]", "-map", "0:a", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "copy", "-t", str(DUR), v3)
# 5) captions on top of everything
ass = os.path.join(BD, "captions.ass"); v4 = os.path.join(BD, "4_captions.mp4")
run("python3", os.path.join(ROOT, "captions", "captions.py"), words, ass, "--emphasis", ";".join(emph), "--end", DUR, "--fix", R.get("fix", ""), "--style", os.path.join(BD, "style.json"))
run("ffmpeg", "-v", "error", "-y", "-i", v3, "-vf", f"ass={ass}", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "copy", v4)
# 6) sound (generated unless the recipe already points at a bed), then finish and checks
song = R.get("song") or ""
sfx_dir = ""
if not song or song in ("generate", "auto") or not os.path.exists(P(song) if song else ""):
    manifest = generate_sound(BD, style=style, provider=R.get("sound_provider", "auto"), duration_s=max(8.0, DUR))
    song = manifest["bed"]
    sfx_dir = os.path.dirname(manifest["cue_map"])
else:
    song = P(song)
cap = style["captions"]
hook_box = [80, int(style["hook"]["y"]), 1000, int(style["hook"]["y"]) + 220]
cap_bottom = 1920 - int(cap["safe_bottom"])
cap_box = [int(cap["margin_h"]), cap_bottom - int(cap["size"]) * 2, 1080 - int(cap["margin_h"]), cap_bottom]
layout = {"caption_boxes": [cap_box], "text_boxes": [{"name": "caption", "box": cap_box}]}
if hook:
    layout["text_boxes"].insert(0, {"name": "hook", "box": hook_box})
layout_path = os.path.join(BD, "layout.json")
json.dump(layout, open(layout_path, "w"))
cj = os.path.join(BD, "cues.json")
json.dump({"song": song, "song_offset": R.get("song_offset", 0), "names": list(RR.AGENTS), "border": bool(style["border"]["enabled"]),
           "sfx_dir": sfx_dir, "audio": style["audio"], "hook": {"t": 0, "dur": HD} if hook else None,
           "punchins": json.load(open(pi + ".punchins.json"))["punchins"], "words": WORDS, "joins": joins, "face_joins": face_joins, "glitches": auto,
           "shots": [[round(a, 3), round(b, 3), k] for a, b, k in shots_now()], "cues": sorted(cues, key=lambda c: c["t"])}, open(cj, "w"), indent=1)
out = R.get("out", "final.mp4"); out = out if os.path.isabs(out) else os.path.join(D, out)
run("python3", f"{B}/finish.py", v4, cj, out)
r = subprocess.run(["python3", os.path.join(ROOT, "qa", "verify.py"), out, "--style", os.path.join(BD, "style.json"), "--layout", layout_path, "--json", out + ".verify.json"])
sys.exit(r.returncode)
