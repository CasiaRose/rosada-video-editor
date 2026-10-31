"""Frame-exact compositor (numpy/OpenCV/PIL), renders one chunk so you can run 2 workers and resume.
Usage: python composite.py <start> <end_exclusive>   -> render/chunk_<start>.mp4 (video only, captions burned by libass)
Layer order (keep it): base (FACE w/ stepped punch-in | BROLL clip | PANEL_F backdrop) -> full-frame panel -> docked panels ->
hook card -> terminal callouts -> glitch (cut frame +0..2) -> progress border -> captions (ass filter, LAST so nothing covers them).
Inputs: beats.json, facetrack.json, clips/aroll.mp4, broll clips (1080x1920 30fps, exact length of their segment), captions.ass,
optional panels.py exposing PANELS {name:(f0,f1,kind,w,h,cx,cy)} and DRAW {name: fn(global_frame)->PIL RGBA}, plus CUES for mix.py."""
import sys, os, json, subprocess, importlib, numpy as np, cv2
import pk, glitch, pborder
from PIL import Image
B = json.load(open("beats.json")); W, H = 1080, 1920; N = json.load(open("timeline.json"))["N"]
FT = json.load(open("facetrack.json"))
SEG = {}
for nm, a, b, kind in B["segments"]:
    for n in range(a, b + 1): SEG[n] = (nm, a, b, kind)
assert len(SEG) == N, f"segments cover {len(SEG)} frames, timeline N={N}"
GL = {c: co for c, co in B.get("glitch", [])}; ZOOM = B.get("zoom", [[0, 1.0]]); HARD = set(B.get("zoom_hard", []))
try: panels = importlib.import_module(B.get("panels_module", "panels"))
except ModuleNotFoundError: panels = None
BD = pk.backdrop()
def read_clip(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "scale=1080:1920:in_color_matrix=bt709:in_range=tv", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
CLIPS = {}
def clip(nm):
    if nm not in CLIPS:
        p = B["broll"][nm]; CLIPS[nm] = np.load(p, mmap_mode="r") if p.endswith(".npy") else read_clip(p)
    return CLIPS[nm]
def zoom_at(n):
    k = max(i for i, (f, s) in enumerate(ZOOM) if f <= n); f, s = ZOOM[k]
    prev = s if (k == 0 or f in HARD) else ZOOM[k - 1][1]          # HARD = step lands on a cut/join: no ease
    t = min(1, (n - f + 1) / 4); return prev + (s - prev) * pk.ease(t)  # otherwise 4-frame smoothstep ease
def face(fr, n):
    s = zoom_at(n)
    if abs(s - 1) < 1e-4: return fr.astype(np.float32)
    ax, ay = FT["ax"][n], FT["ay"][n]
    M = np.float32([[s, 0, ax - s * ax], [0, s, ay - s * ay]])      # scale about the eye line, sub-pixel (no integer-rounding holds)
    return cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
CARD = B.get("card"); CARD_IM = Image.open(CARD["png"]).convert("RGBA") if CARD and os.path.exists(CARD.get("png", "")) else None
A_CARD = {CARD["f1"] - 5 + i: v for i, v in enumerate((0.91, 0.71, 0.25, 0.03, 0.0, 0.0))} if CARD else {}
def clean(n, fr):
    nm, a, b, kind = SEG[n]; l = n - a
    if kind == "FACE": img = face(fr, n)
    elif kind == "BROLL": img = np.asarray(clip(nm)[min(l, len(clip(nm)) - 1)]).astype(np.float32)
    else: img = BD.copy()
    if panels and nm in panels.PANELS and panels.PANELS[nm][2] == "F":          # full-frame panel on the backdrop
        f0, f1, _, w, h, cx, cy = panels.PANELS[nm]; l = n - f0
        sc = 0.965 + 0.035 * pk.ease_out(l / 6); al = min(1, (l + 1) / 3)        # 6-frame settle, 3-frame fade
        sc *= 1.0 + 0.018 * l / max(1, f1 - f0)                                   # slow 1.8% living push: holds never read as frozen
        sw = (l - 3) / 11 if 3 <= l <= 14 else None                               # light sweep frames 3..14 after entrance
        pk.place(img, panels.DRAW[nm](n), cx, cy, sc, al, sweep=sw)
    for dn, f0, f1 in B.get("docked", []):                                        # docked top-third panel over the face
        if panels and f0 <= n <= f1:
            l = n - f0; r = f1 - n; _, _, _, w, h, cx, cy = panels.PANELS[dn]
            ai = pk.ease_out((l + 1) / 6); ao = min(1, r / 5) if r < 5 else 1
            sc = (0.94 + 0.06 * pk.back_out(min(1, (l + 1) / 7), 1.2)) * (0.97 + 0.03 * ao)
            sw = (l - 2) / 11 if 2 <= l <= 13 else None
            pk.place(img, panels.DRAW[dn](n), cx, cy - 16 * (1 - ai), sc, ai * pk.ease(ao), sweep=sw)
    if CARD_IM is not None and CARD["f0"] <= n <= CARD["f1"]:
        a = A_CARD.get(n, 1.0)
        if a > 0: pk.place(img, CARD_IM, 540, CARD.get("cy", 150) + CARD_IM.height // 2, 1.0, a)
    for f0, f1, s in B.get("callouts", []):
        if f0 <= n <= f1:
            a = pk.CALLOUT_ALPHA_IN.get(n - f0, 1.0) * pk.CALLOUT_ALPHA_OUT.get(f1 - n, 1.0)
            pk.place(img, pk.draw_callout(n - f0, s), 540, 282, 1.0, a, shadow=False)   # y 282: under the top UI band, above the face
    return img
def main(c0, c1):
    os.makedirs("render", exist_ok=True); out = f"render/chunk_{c0:04d}.mp4"
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{c0/30:.5f}", "-i", "clips/aroll.mp4", "-frames:v", str(c1 - c0), "-vf", "scale=in_color_matrix=bt709:in_range=tv",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-vf", f"setpts=PTS+{c0/30:.5f}/TB,ass=captions.ass,setpts=PTS-STARTPTS,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-pix_fmt", "yuv420p",
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", out + ".part.mp4"], stdin=subprocess.PIPE)
    prev_img = None; cutprev = {}
    for n in range(c0, c1):
        fr = np.frombuffer(dec.stdout.read(W * H * 3), np.uint8).reshape(H, W, 3)
        img = clean(n, fr); cln = img
        for c, co in GL.items():
            if c <= n <= c + 2:
                if c not in cutprev: cutprev[c] = prev_img if (prev_img is not None and n == c) else None
                pv = cutprev[c] if cutprev[c] is not None else img
                img = glitch.apply(np.clip(img, 0, 255).astype(np.uint8), np.clip(pv, 0, 255).astype(np.uint8), n - c, c, co).astype(np.float32)
        prev_img = cln
        enc.stdin.write(pborder.apply(np.clip(img, 0, 255).astype(np.uint8), n).tobytes())
        if n % 50 == 0: print(n, flush=True)
    enc.stdin.close(); enc.wait(); dec.wait(); os.replace(out + ".part.mp4", out); print("done", out, flush=True)
if __name__ == "__main__": main(int(sys.argv[1]), int(sys.argv[2]))
