"""VO track: raw audio (already on the video clock, audio/raw48_vc.wav) -> keeps joined with 20 ms equal-power crossfades centred
on each join (length-preserving) -> atempo 1.1 -> HPF 80 Hz -> gentle denoise -> +gain -> padded/trimmed to EXACTLY N/fps s.
Writes audio/vo.wav (48k mono f32). Usage: python vo.py"""
import numpy as np, subprocess, json
cfg = json.load(open("config.json")); SR = 48000
T = json.load(open("timeline.json")); K = T["keeps"]; N = T["N"]; FPS = T.get("fps", 30); SP = T["speed"]
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", "audio/raw48_vc.wav", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout, np.float32)
X = 0.010; segs = []
for j, (a, b) in enumerate(K):
    a2 = a - (X if j else 0); b2 = b + (X if j < len(K) - 1 else 0)
    segs.append(x[int(round(a2 * SR)):int(round(b2 * SR))].astype(np.float64))
n = int(round(2 * X * SR)); t = np.linspace(0, np.pi / 2, n); fi, fo = np.sin(t), np.cos(t)
y = segs[0]
for s in segs[1:]: y = np.concatenate([y[:-n], y[-n:] * fo + s[:n] * fi, s[n:]])
print("joined", round(len(y) / SR, 4), "expected", round(sum(b - a for a, b in K), 4))
y.astype(np.float32).tofile("audio/vo_joined.f32")
tgt = N / FPS
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "audio/vo_joined.f32", "-af",
                f"atempo={SP},highpass=f=80,afftdn=nr=10:nf=-60:tn=1,volume={cfg.get('vo_gain_db', 14)}dB,apad,atrim=0:{tgt:.4f}",
                "-c:a", "pcm_f32le", "audio/vo.wav"], check=True)
print("vo.wav target", round(tgt, 4))
