"""A-roll: raw keeps at 1.1x -> exactly N frames (nearest-frame mapping through the SAME keeps as vo.py, so lip sync is structural),
mild face grade (LUT ~1.032x-11) + light unsharp. Writes clips/aroll.mp4 (crf 10 intermediate) + aroll_map.json (out frame -> raw frame).
Usage: python aroll.py   Speed-up note: video uses frame re-mapping (equivalent of setpts=PTS/1.1), audio uses atempo=1.1 in vo.py.
Simple single-file equivalent (no keeps): ffmpeg -i raw.mov -filter_complex "[0:v]setpts=PTS/1.1[v];[0:a]atempo=1.1[a]" -map "[v]" -map "[a]" -r 30 out.mp4"""
import json, subprocess, numpy as np, cv2, os
cfg = json.load(open("config.json")); T = json.load(open("timeline.json")); K = T["keeps"]; N = T["N"]; SP = T["speed"]; FPS = T.get("fps", 30)
nraw = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", cfg["raw"]], capture_output=True, text=True).stdout.strip())
def inv(t):
    o = t * SP
    for a, b in K:
        if o <= b - a: return a + o
        o -= b - a
    return K[-1][1]
idx = [min(nraw - 1, int(round(inv((n + 0.5) / FPS) * FPS - 0.5))) for n in range(N)]
json.dump(idx, open("aroll_map.json", "w")); os.makedirs("clips", exist_ok=True)
W, H = 1080, 1920
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", cfg["raw"], "-vf", f"scale={W}:{H}:in_color_matrix=bt709:in_range=tv", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "10", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "clips/aroll.mp4"], stdin=subprocess.PIPE)
LUT = np.clip(np.arange(256) * 1.032 - 11.0, 0, 255).astype(np.uint8)
need = {}
for n, r in enumerate(idx): need.setdefault(r, []).append(n)
k = 0
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    if k in need:
        f = LUT[np.frombuffer(b, np.uint8).reshape(H, W, 3)]
        bl = cv2.GaussianBlur(f, (0, 0), 1.0); f = cv2.addWeighted(f, 1.25, bl, -0.25, 0)
        for _ in need[k]: enc.stdin.write(f.tobytes())
    k += 1
    if k > idx[-1]: break
enc.stdin.close(); enc.wait(); dec.kill(); print("N", N, "dup frames", N - len(set(idx)))
