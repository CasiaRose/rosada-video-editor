#!/usr/bin/env python3
"""Optional progress border (accent to second accent, clockwise, closes on the last frame).
  python3 border.py in.mp4 out.mp4            # burn border onto a finished 1080x1920 30fps video (audio copied)
  python3 border.py --overlay N out.mov        # pre-render a transparent overlay (qtrle+alpha) for an N-frame video
  then: ffmpeg -i in.mp4 -i out.mov -filter_complex "[0][1]overlay=0:0" ...   (overlay approach)
The overlay is derived exactly from the core renderer: render on black and on white -> alpha + colour."""
import os, sys, subprocess, numpy as np
def nframes(src):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-count_packets","-show_entries","stream=nb_read_packets","-of","csv=p=0",src],capture_output=True,text=True).stdout
    return int(r.strip())
def rgba_frames(N):
    os.environ["PB_N"] = str(N)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import pborder_core as pb
    D, A_, P = pb.DIST.astype(np.float32), pb.ARC.astype(np.float32), None
    stroke = np.clip(pb.SW / 2 + 0.5 - D, 0, 1); col = (pb.PRI[None] + (pb.COR - pb.PRI)[None] * (A_ / pb.LEN)[:, None]).astype(np.float32)
    gbase = (pb.GLOW_G * np.exp(-np.maximum(D, 0) ** 2 / (2 * pb.GLOW_S ** 2))).astype(np.float32)
    PAP, COR = pb.PAP.astype(np.float32), pb.COR.astype(np.float32); buf = np.zeros((pb.H, pb.W, 4), np.uint8)
    def over(C, A, a, c): return C * (1 - a[:, None]) + c * a[:, None], A * (1 - a) + a
    for n in range(N):
        sh = min(1.0, (n + 1) / N) * pb.LEN; filled = np.clip(sh - A_ + 0.5, 0, 1)
        C = np.zeros((len(D), 3), np.float32); A = np.zeros(len(D), np.float32)
        C, A = over(C, A, pb.TRACK_A * stroke * (1 - filled), PAP[None])
        ga = np.maximum(gbase * np.clip((sh - A_) / 10 + 0.5, 0, 1) - stroke * filled, 0); C, A = over(C, A, ga, col)
        C, A = over(C, A, stroke * filled, col)
        hx, hy = pb.head_xy(max(0, sh - pb.DOT_BACK)); dd = np.hypot(pb.PX - hx, pb.PY - hy).astype(np.float32)
        dg = pb.DOT_GLOW_G * np.exp(-np.maximum(dd - pb.DOT_R, 0) ** 2 / (2 * pb.DOT_GLOW_S ** 2)) * (dd > pb.DOT_R - 1); C, A = over(C, A, dg, COR[None])
        C, A = over(C, A, np.clip(pb.DOT_R + 0.5 - dd, 0, 1), PAP[None])
        rgb = np.where(A[:, None] > 1e-3, C / np.maximum(A[:, None], 1e-3), 0)
        buf[pb.inband] = np.dstack([np.clip(rgb, 0, 255), (A * 255)[:, None]])[:, 0].round().astype(np.uint8) if False else np.concatenate([np.clip(rgb, 0, 255), (A * 255)[:, None]], 1).round().astype(np.uint8)
        yield buf
if __name__ == "__main__":
    if sys.argv[1] == "--overlay":
        N = int(sys.argv[2]); out = sys.argv[3]
        e = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgba","-s","1080x1920","-r","30","-i","-","-c:v","qtrle",out], stdin=subprocess.PIPE)
        for f in rgba_frames(N): e.stdin.write(f.tobytes())
        e.stdin.close(); e.wait(); print("overlay", out, N); raise SystemExit
    src, dst = sys.argv[1], sys.argv[2]; N = nframes(src)
    e = subprocess.Popen(["ffmpeg","-v","error","-y","-i",src,"-f","rawvideo","-pix_fmt","rgba","-s","1080x1920","-r","30","-i","-",
        "-filter_complex","[0:v]scale=1080:1920,setsar=1,fps=30[b];[b][1:v]overlay=0:0:format=auto,format=yuv420p[v]","-map","[v]","-map","0:a?",
        "-c:v","libx264","-crf","18","-preset","medium","-c:a","copy","-movflags","+faststart",dst], stdin=subprocess.PIPE)
    for f in rgba_frames(N): e.stdin.write(f.tobytes())
    e.stdin.close(); rc = e.wait(); print("bordered", dst, N, "frames"); sys.exit(rc)
