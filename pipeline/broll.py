"""B-roll clip builder: landscape screen capture / HQ footage -> 1080x1920 moving crop of EXACT length, no held frames.
Usage (as a library):  from broll import build; build("src.mp4", t0=229.8, n_out=45, out="clips/HQ1.mp4", path=[(cx,top,h),(cx,top,h)])
- decodes the window, drops capture repeats (screen recordings of the 3D app are VFR and hitch), lays unique frames 1:1 at 30 fps,
- moves the crop (cx, top, crop height in source px) along the eased path, Lanczos + light unsharp,
- if there are fewer unique frames than needed, it continues with a slow eased digital push instead of freezing.
Crop OUT browser chrome / bookmark bars / localhost URLs / app toolbars / room labels; inpaint cursors (cv2.inpaint with a dilated mask)."""
import subprocess, numpy as np, cv2
OW, OH = 1080, 1920
def crop_scale(f, cx, top, h):
    w = h * OW / OH; x0 = cx - w / 2
    M = np.float32([[OW / w, 0, -x0 * OW / w], [0, OH / h, -top * OH / h]])
    out = cv2.warpAffine(np.ascontiguousarray(f), M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    return cv2.addWeighted(out, 1.35, cv2.GaussianBlur(out, (0, 0), 1.2), -0.35, 0)
def smoother(t): return t ** 3 * (t * (6 * t - 15) + 10)
def dedup(F, motion_thr=2.0):
    """drop exact capture repeats: diff<0.03, or diff<0.2 while the camera is moving (neighbour diffs > motion_thr)."""
    d = [99] + [float(np.abs(F[i].astype(np.int16)[::4, ::4] - F[i - 1].astype(np.int16)[::4, ::4]).mean()) for i in range(1, len(F))]
    keep = [i for i in range(len(F)) if not (i and (d[i] < 0.03 or (d[i] < 0.2 and max(d[i - 1] if i > 1 else 0, d[i + 1] if i + 1 < len(F) else 0) > motion_thr)))]
    return keep, d
def decode(src, t0, n):
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip().split(","))
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", src, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.uint8).reshape(-1, h, w, 3).copy()
def build(src, t0, n_out, out, path, extra=1.6, push_end=1.035):
    F = decode(src, t0, int(n_out * extra) + 8); keep, _ = dedup(F); U = [F[i] for i in keep]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", "30", "-i", "-", "-c:v", "libx264", "-crf", "12",
                            "-preset", "fast", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", out], stdin=subprocess.PIPE)
    (c0, t0_, h0), (c1, t1_, h1) = path[0], path[-1]
    for k in range(n_out):
        u = smoother(k / max(1, n_out - 1)); f = U[min(k, len(U) - 1)]
        z = 1 + (push_end - 1) * max(0, (k - len(U) + 1) / max(1, n_out - len(U))) if k >= len(U) else 1.0   # glide instead of freeze
        h = (h0 + (h1 - h0) * u) / z; cx = c0 + (c1 - c0) * u; top = t0_ + (t1_ - t0_) * u + (h0 + (h1 - h0) * u - h) / 2
        enc.stdin.write(crop_scale(f, cx, top, h).tobytes())
    enc.stdin.close(); enc.wait(); print(out, "unique", len(U), "needed", n_out)
