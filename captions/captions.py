#!/usr/bin/env python3
"""Captions from a words JSON and a style profile. Burn with: ffmpeg -vf ass=captions.ass
  python3 captions.py words.json captions.ass --style style.json --emphasis "goal:accent" --end 19.5
modes: block (one colour), karaoke (active word uses caption_active), none.
"""
import os, sys, json, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from style.profile import NEUTRAL, load_profile
ap = argparse.ArgumentParser(); ap.add_argument("words"); ap.add_argument("out"); ap.add_argument("--style", default=""); ap.add_argument("--emphasis", default=""); ap.add_argument("--end", type=float); ap.add_argument("--fix", default="")
A = ap.parse_args(); J = json.load(open(A.words))
style = load_profile(A.style) if A.style else NEUTRAL
CAP, COLR = style["captions"], style["colors"]
if CAP["mode"] == "none":
    open(A.out, "w").write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    print("captions: mode none"); raise SystemExit
def ass_bgr(hex_color):
    h = hex_color.lstrip("#"); return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&"
W = [dict(t=w["word"].strip(), s=w["start"], e=w["end"]) for s in J["segments"] for w in s["words"]] if isinstance(J, dict) else [dict(t=(w.get("w") or w.get("word")).strip(), s=w.get("s", w.get("start")), e=w.get("e", w.get("end"))) for w in J]
fx = dict(kv.split("=") for kv in A.fix.split(",") if "=" in kv)
for w in W:
    core = w["t"].strip(",.?!"); w["t"] = w["t"].replace(core, fx.get(core, core)).replace("*", "")
for i in range(1, len(W)):
    if W[i]["s"] <= W[i - 1]["s"] + 0.05: W[i]["s"] = round(W[i - 1]["s"] + 0.06, 3)
END = A.end or (W[-1]["e"] + 0.6)
EM = {}
for kv in A.emphasis.split(";"):
    if not kv.strip(): continue
    word, col = (kv.split(":") + ["PRI"])[:2]
    for i, w in enumerate(W):
        if w["t"].strip(",.?!").lower() == word.strip().lower(): EM[i] = col.strip().upper()
FORCE = set()
for i in EM: FORCE |= {i, i + 1}
groups, cur = [], []
for i, w in enumerate(W):
    txt = " ".join(W[j]["t"] for j in cur + [i])
    if cur and (len(cur) >= int(CAP["max_words"]) or len(txt) > (int(CAP["max_chars"]) + 2 if i in EM else int(CAP["max_chars"])) or i in FORCE or W[cur[-1]]["t"][-1] in ",.?!"): groups.append(cur); cur = []
    cur.append(i)
groups.append(cur)
ACTIVE = ass_bgr(COLR["caption_active"]); BASE = ass_bgr(COLR["caption"]); ACCENT = ass_bgr(COLR["accent"]); ACCENT2 = ass_bgr(COLR["accent_2"])
NAMED = {"ACCENT": ACCENT, "ACCENT_2": ACCENT2, "1": ACCENT, "2": ACCENT2}
ts = lambda t: f"{int(max(0,t)//3600)}:{int(max(0,t)%3600//60):02d}:{max(0,t)%60:05.2f}"
ev = []
for gi, g in enumerate(groups):
    g_end = W[groups[gi + 1][0]]["s"] if gi + 1 < len(groups) else END
    if gi + 1 < len(groups) and g_end - W[g[-1]]["e"] > 0.45: g_end = W[g[-1]]["e"] + 0.25
    for k, i in enumerate(g):
        a = W[i]["s"]; b = W[g[k + 1]]["s"] if k + 1 < len(g) else g_end
        if b <= a: continue
        parts = []
        for j in g:
            t = W[j]["t"]
            if CAP["mode"] == "karaoke" and j == i:
                parts.append("{\\c" + ACTIVE + "}" + t + "{\\c" + BASE + "}")
            elif j in EM and CAP["animation"] == "pop" and a >= W[j]["s"] - 1e-6:
                anim = r"\fscx100\fscy100\t(0,110,\fscx118\fscy118)\t(110,240,\fscx112\fscy112)" if j == i else r"\fscx112\fscy112"
                parts.append("{\\b1\\c" + NAMED.get(EM[j], ACCENT) + anim + "}" + t + "{\\c" + BASE + "\\fscx100\\fscy100}")
            elif j in EM:
                parts.append("{\\b1\\c" + NAMED.get(EM[j], ACCENT) + "}" + t + "{\\c" + BASE + "}")
            else: parts.append(t)
        ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},Cap,,0,0,0,,{' '.join(parts)}")
style_line = "Style: Cap,{font},{size},{base},{base},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,{ml},{ml},{mv},1".format(
    font=style["fonts"]["caption"], size=int(CAP["size"]), base=BASE, outline=int(CAP["outline"]), shadow=int(CAP["shadow"]), ml=int(CAP["margin_h"]), mv=int(CAP["margin_v"]))
open(A.out, "w").write("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
""" + style_line + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + "\n".join(ev) + "\n")
print(f"captions: {len(groups)} groups, {len(EM)} emphasis words -> {A.out}")
