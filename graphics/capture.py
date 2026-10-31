#!/usr/bin/env python3
"""Capture a panel template to video at 1080x1920, 30 fps.
  python3 capture.py params/agent_intro.json out.mov            # transparent overlay, qtrle .mov with alpha (default when bg is "none")
  python3 capture.py params/stat_goal.json out.mp4              # opaque H.264 (use with "bg":"green" for full-frame panels)
  python3 capture.py params/hook.json frames_dir/ --png         # transparent PNG sequence frames_dir/f_0000.png ...
  python3 capture.py params/x.json out.mov --still 45 still.png # also save one still (frame 45)
Also writes <out>.cues.json: the SFX cues for this graphic (panel_in / panel_out / type_tick) relative to the graphic start;
add your placement time to each t and merge into the edit's cues.json.
Needs: pip install playwright && playwright install chromium   (or set CHROME=/path/to/Chrome). Font: Inter installed (fc-list | grep Inter)."""
import sys, os, json, subprocess, pathlib
from playwright.sync_api import sync_playwright
args = sys.argv[1:]; pj, out = args[0], args[1]; png = "--png" in args
still = (int(args[args.index("--still") + 1]), args[args.index("--still") + 2]) if "--still" in args else None
P = json.load(open(pj)); trans = P.get("bg", "none") == "none"
here = pathlib.Path(__file__).resolve().parent; url = (here / "templates.html").as_uri()
N = round(P.get("dur", 4) * 30)
with sync_playwright() as pw:
    exe = os.environ.get("CHROME") or next((c for c in ["/usr/bin/google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if os.path.exists(c)), None)
    try: b = pw.chromium.launch()
    except Exception: b = pw.chromium.launch(executable_path=exe)
    pg = b.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    pg.add_init_script("window.PARAMS=" + json.dumps(P) + ";")
    pg.goto(url); pg.wait_for_function("window.READY"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
    if png: os.makedirs(out, exist_ok=True); ff = None
    else:
        enc = ["-c:v", "qtrle"] if (trans and out.endswith(".mov")) else ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", "30", "-i", "-"] + enc + [out], stdin=subprocess.PIPE)
    for i in range(N):
        pg.evaluate("t=>render(t)", i / 30)
        buf = pg.screenshot(type="png", omit_background=trans)
        if png: open(f"{out}/f_{i:04d}.png", "wb").write(buf)
        else: ff.stdin.write(buf)
        if still and i == still[0]: open(still[1], "wb").write(buf)
    if ff: ff.stdin.close(); ff.wait()
    b.close()
# SFX cues for this graphic (times relative to graphic start, seconds)
cues = []
if P.get("scene") == "terminal":
    s = P.get("text", "> goal: $10,000 · due 12/31"); tf = P.get("type_frames", 18)
    cues += [{"t": round((3 + (c * tf) / len(s)) / 30, 3), "event": "type_tick"} for c in range(0, len(s), 3)]
elif P.get("scene") == "hook_broll":
    cf = P.get("chip_frame", 12)
    cues += [{"t": 0.167, "event": "panel_in"}, {"t": round((3 + 6) / 30, 3), "event": "whoosh"}, {"t": round((cf + 3) / 30, 3), "event": "riser_hit"}]
else:
    cues.append({"t": 0.0, "event": "panel_in"})
    for r in P.get("rows", []):
        if r.get("done"): cues.append({"t": round((r.get("frame", 0) + r.get("check_delay", 4)) / 30, 3), "event": "chip_pop", "_only_if": "it's a key moment (max 1-2 per panel)"})
    if P.get("scene") == "flow":
        cues += [{"t": round(d.get("frame", 6 + i * 5) / 30, 3), "event": "pop"} for i, d in enumerate(P.get("nodes", [])) if d.get("hot")]
        cues.append({"t": round(P.get("done_frame", 60) / 30, 3), "event": "chip_pop"})
if P.get("out", True): cues.append({"t": round((N - 1) / 30, 3), "event": "panel_out"})
json.dump({"graphic": os.path.basename(out), "frames": N, "cues": cues}, open(str(out).rstrip("/") + ".cues.json", "w"), indent=1)
print("captured", out, N, "frames", "alpha" if trans else "opaque")
