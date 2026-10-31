"""Audio mix: VO (-16 LUFS) + music bed (18 dB under the VO, +6 dB in pauses, 50 ms down / 120 ms up) + SFX cues -> 2-pass loudnorm
-14 LUFS / TP -1.5 / LRA 11 -> audio/mix.wav (48k stereo 24-bit) + audio/mix_log.json.  Usage: python mix.py [--stems]
--stems writes audio/stem_{vo,music,sfx}.npy for the checker and exits. RE-RUN --stems AFTER EVERY MIX CHANGE (stale stems = false check results).
SFX levels (dB relative to the normalised SFX peak, before the +1.5 dB bus trim): glitch -21, pop (zoom >=1.15) -20, tick (smaller zoom) -23,
swish_in (docked panel in) -22, swish_out -25, scratch (arrow draw-on) -27, key ticks (callout type-on) -34, panel cues as listed by panels.CUES."""
import json, subprocess, sys, importlib, numpy as np
cfg = json.load(open("config.json")); B = json.load(open("beats.json")); SR = 48000; N = json.load(open("timeline.json"))["N"]; L = int(round(N / 30 * SR))
def load(p, ch=1):
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).reshape(-1, ch).astype(np.float64)
def lufs(x):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f64le", "-ar", str(SR), "-ac", str(x.shape[1]), "-i", "-", "-af", "ebur128", "-f", "null", "-"], input=x.tobytes(), capture_output=True)
    t = p.stderr.decode(); i = t.rfind("I:"); return float(t[i + 2:].split("LUFS")[0])
vo = load("audio/vo.wav")[:L, 0]; vo = np.pad(vo, (0, L - len(vo)))
mus = load(cfg["music"], 2)[:L]; mus = np.pad(mus, ((0, L - len(mus)), (0, 0)))
g = 10 ** ((-16 - lufs(np.repeat(vo[:, None], 2, 1))) / 20); vo *= g                      # VO -> -16 LUFS (dual mono)
hop = 960; edb = 20 * np.log10(np.array([np.sqrt(np.mean(vo[i:i + hop] ** 2) + 1e-12) for i in range(0, L, hop)]))
act = edb > (np.percentile(edb, 90) - 22); a = act.copy()
for i in range(len(a)):                                                                  # 150 ms hangover
    if act[max(0, i - 3):i + 1].any(): a[i] = True
k = 0
while k < len(a):                                                                        # gaps < 300 ms count as speech
    if not a[k]:
        j = k
        while j < len(a) and not a[j]: j += 1
        if j - k < 7 and k > 0 and j < len(a): a[k:j] = True
        k = j
    else: k += 1
mus_l = lufs(mus); base = 10 ** ((-16 - 18 - mus_l) / 20)                                # bed 18 dB under VO
tgt = np.where(a, 0.0, 6.0); cur = 0.0; gdb = np.zeros(len(tgt))                         # +6 dB in pauses
for i, t in enumerate(tgt):
    cur += (t - cur) * min(1, 0.02 / 0.05 if t < cur else 0.02 / 0.12); gdb[i] = cur      # 50 ms duck, 120 ms release
gcurve = np.interp(np.arange(L), np.arange(len(gdb)) * hop + hop / 2, gdb)
fade = np.ones(L); fade[:int(0.25 * SR)] = np.linspace(0.3, 1, int(0.25 * SR)); fo = int(1.2 * SR); fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
music = mus * (base * 10 ** (gcurve / 20) * fade)[:, None]
D = cfg.get("sfx_dir", "./sfx") + "/"
def glitch_sfx():
    rng = np.random.default_rng(5); n = int(0.16 * SR); y = np.zeros(n)
    for st, ln in ((0, 0.035), (0.05, 0.025), (0.09, 0.05)):
        s0 = int(st * SR); m = int(ln * SR); z = rng.normal(0, 1, m); hold = 6 + int(rng.integers(0, 10)); z = np.repeat(z[::hold], hold)[:m]
        tone = np.sin(2 * np.pi * (900 + 600 * rng.random()) * np.arange(m) / SR); y[s0:s0 + m] += (0.55 * z + 0.45 * np.sign(tone)) * np.exp(-np.arange(m) / (0.4 * m))
    Y = np.fft.rfft(y); f = np.fft.rfftfreq(n, 1 / SR); Y[(f < 300) | (f > 7000)] *= 0.15; y = np.fft.irfft(Y, n); return y / np.abs(y).max() * 0.5
def scratch_sfx():
    rng = np.random.default_rng(9); n = int(0.22 * SR); Z = np.fft.rfft(rng.normal(0, 1, n)); f = np.fft.rfftfreq(n, 1 / SR); Z[(f < 1800) | (f > 9000)] *= 0.05; z = np.fft.irfft(Z, n)
    t = np.arange(n) / SR; y = z * (0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 23 * t))) * np.minimum(1, t / 0.02) * np.minimum(1, (0.22 - t) / 0.06); return y / np.abs(y).max() * 0.5
S = {k: load(D + f)[:, 0] for k, f in (("tick", "tick_soft.wav"), ("pop", "pop_soft.wav"), ("swish_in", "air_swish_in.wav"), ("swish_out", "air_swish_out.wav"),
                                       ("whoosh_in", "whoosh_soft_in.wav"), ("whoosh_out", "whoosh_soft_out.wav"), ("door", "door_click_soft.wav"))}
S["key"] = S["tick"]; S["glitch"] = glitch_sfx(); S["scratch"] = scratch_sfx()
cues = []
try: cues += [(f, s, db, "panel") for f, s, db in importlib.import_module(B.get("panels_module", "panels")).CUES]
except ModuleNotFoundError: pass
import pk
for f0, f1, s in B.get("callouts", []): cues += [(f, n, db, "panel") for f, n, db in pk.callout_keys(f0, s)]
cues += [(c, "glitch", -21, "glitch") for c, _ in B.get("glitch", [])]
hard = set(B.get("zoom_hard", []))
cues += [(f, "pop" if s >= 1.15 else "tick", -20 if s >= 1.15 else -23, "zoom") for f, s in B.get("zoom", []) if f and f not in hard]
for dn, f0, f1 in B.get("docked", []): cues += [(f0, "swish_in", -22, "dock"), (f1 - 4, "swish_out", -25, "dock")]
cues += [(f, s, db, "extra") for f, s, db in B.get("extra_sfx", [])]          # e.g. [frame, "whoosh_in", -22] at b-roll in
pri = {"glitch": 0, "zoom": 1, "dock": 2, "panel": 3, "extra": 3}; kept = []
for c in sorted(cues, key=lambda c: (pri[c[3]], c[0])):                       # no stacking within 120 ms (key ticks exempt among themselves)
    if any(abs(k[0] - c[0]) * 1000 / 30 < 120 and k[1] != "key" for k in kept): continue
    kept.append(c)
kept.sort(); sfx = np.zeros(L)
for f, s, db, src in kept:
    x = S[s] * 10 ** (db / 20) / max(1e-6, np.abs(S[s]).max()) * 0.5; st = int(f / 30 * SR)
    if s in ("swish_in", "whoosh_in"): st -= int(np.argmax(np.abs(x)))         # swell peak lands ON the frame
    st = max(0, st); e = min(L, st + len(x)); sfx[st:e] += x[:e - st]
sfx *= 10 ** (1.5 / 20)                                                        # bus trim +1.5 dB (owner said SFX were too quiet at +0)
mix = vo[:, None] + music + sfx[:, None]
if "--stems" in sys.argv:
    for n, v in (("vo", vo), ("music", music.mean(1)), ("sfx", sfx)): np.save(f"audio/stem_{n}.npy", v.astype(np.float32))
    np.save("audio/music_gain_db.npy", gdb.astype(np.float32)); np.save("audio/speech_act.npy", a); print("stems saved"); raise SystemExit
pre = "audio/premix.f64"; mix.astype(np.float64).tofile(pre)
p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
j = json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])
af = f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", pre, "-af", af + ",aresample=48000", "-c:a", "pcm_s24le", "audio/mix.wav"], check=True)
json.dump(dict(vo_gain_db=round(20 * np.log10(g), 2), music_lufs_raw=mus_l, loudnorm_in=j, cues=kept, dropped=[c for c in cues if c not in kept]), open("audio/mix_log.json", "w"), indent=0)
print("cues kept", len(kept), "dropped", len(cues) - len(kept))
