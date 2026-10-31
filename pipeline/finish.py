#!/usr/bin/env python3
"""Finish pass: optional border, ducked bed, effects, loudness from the style profile.
  python3 finish.py in.mp4 cues.json out.mp4
cues.json:
 {"song": "path/to/bed.wav", "song_offset": 0, "vo": "vo.wav",
  "border": false, "sfx_dir": "cache/sound/<id>",
  "audio": {"master_lufs": -14, "true_peak_db": -1.0, "voice_lufs": -16, "bed_under_db": 16, "gap_lift_db": 4},
  "overlays": [{"file": "panel.mov", "t": 1.0}],
  "cues": [{"t": 1.0, "event": "cut"}]}
Writes out.mp4 and out.mp4.mix_log.json."""
import sys, os, json, subprocess, tempfile, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import mix_audio as RA
src, cj, dst = sys.argv[1:4]; C = json.load(open(cj)); _cd = os.path.dirname(os.path.abspath(cj))
fix = lambda p: p if (not p or os.path.isabs(p) or os.path.exists(p)) else os.path.join(_cd, p)
for _o in C.get('overlays', []): _o['file'] = fix(_o['file'])
if C.get('vo'): C['vo'] = fix(C['vo'])
if C.get("song"): C["song"] = fix(C["song"])
RA.apply_audio(C.get("audio"))
if C.get("sfx_dir"): RA.set_sfx_dir(fix(C["sfx_dir"]))
MASTER_I = float((C.get("audio") or {}).get("master_lufs", -14))
MASTER_TP = float((C.get("audio") or {}).get("true_peak_db", -1.0))
SR = RA.SR; tmp = tempfile.mkdtemp(prefix="rfin_")
def run(*a): subprocess.run(a, check=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
N = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
L = int(round(N / 30 * SR)); cues = list(C.get("cues", []))
def cuefile(f):
    for c in (f + '.cues.json', os.path.splitext(f)[0] + '.cues.json'):
        if os.path.exists(c): return c
    return f + '.cues.json'
# 1) overlays
vid = src
if C.get("overlays"):
    ins, fc, last = ["-i", src], "[0:v]null[v0]", "v0"
    for i, o in enumerate(C["overlays"]):
        ins += ["-itsoffset", str(o["t"])] + (["-c:v", "libvpx-vp9"] if o["file"].endswith(".webm") else []) + ["-i", o["file"]]
        fc += f";[{last}][{i+1}:v]overlay=0:0:eof_action=pass:enable='gte(t,{o['t']})'[v{i+1}]"; last = f"v{i+1}"
        if o.get("cues") and os.path.exists(cuefile(o["file"])):
            cues += [{"t": round(o["t"] + c["t"], 3), "event": c["event"]} for c in json.load(open(cuefile(o["file"])))["cues"] if not c.get("_only_if")]
    vid = f"{tmp}/ov.mp4"; run("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", f"[{last}]", "-map", "0:a?", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", vid)
# 2) border
if C.get("border", False):
    run("python3", os.path.join(RA.KIT, "border", "border.py"), vid, f"{tmp}/b.mp4"); vid = f"{tmp}/b.mp4"
# 3) audio
vo = RA.load(C.get("vo") or src)[:L, 0]; vo = np.pad(vo, (0, L - len(vo)))
g = 10 ** ((RA.VO_LUFS - RA.lufs(vo)) / 20); vo *= g
a = RA.speech_activity(vo); hop = 960
mus = RA.song_track(C.get("song"), L, C.get("song_offset", 0)); mus_l = RA.lufs(mus); base = 10 ** ((RA.VO_LUFS - RA.BED_UNDER_DB - mus_l) / 20)
tgt = np.where(a, 0.0, RA.GAP_LIFT_DB); cur = 0.0; gdb = np.zeros(len(tgt))
for i, t in enumerate(tgt): cur += (t - cur) * min(1, 0.02 / 0.05 if t < cur else 0.02 / 0.12); gdb[i] = cur
gc = np.interp(np.arange(L), np.arange(len(gdb)) * hop + hop / 2, gdb)
fade = np.ones(L); fade[:int(.25 * SR)] = np.linspace(.3, 1, int(.25 * SR)); fo = int(1.2 * SR); fade[-fo:] = np.linspace(1, 0, fo) ** 1.5
music = mus * (base * 10 ** (gc / 20) * fade)[:, None]
ex = RA.expand_cues(cues); sfx = np.zeros(L)
for c in ex:
    st = c["start_sample"]; e = min(L, st + len(c["wave"]))
    if st < L: sfx[st:e] += c["wave"][:e - st]
mix = vo[:, None] + music + sfx[:, None]; pre = f"{tmp}/pre.f64"; mix.tofile(pre)
p = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", pre, "-af", f"loudnorm=I={MASTER_I}:TP={MASTER_TP}:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
j = json.loads(p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1])
af = f"loudnorm=I={MASTER_I}:TP={MASTER_TP}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000"
run("ffmpeg", "-v", "error", "-y", "-f", "f64le", "-ar", str(SR), "-ac", "2", "-i", pre, "-af", af, "-c:a", "pcm_s24le", f"{tmp}/mix.wav")
run("ffmpeg", "-v", "error", "-y", "-i", vid, "-i", f"{tmp}/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", dst)
sp = a.astype(bool); vr = np.array([np.sqrt(np.mean(vo[i:i+hop]**2)+1e-12) for i in range(0, L, hop)]); mr = np.array([np.sqrt(np.mean(music[i:i+hop].mean(1)**2)+1e-12) for i in range(0, L, hop)])
log = dict(song=RA.song_path(C.get("song")), vo_gain_db=round(20*np.log10(g), 2), music_under_speech_db=round(20*np.log10(np.sqrt(np.mean(mr[sp]**2))/np.sqrt(np.mean(vr[sp]**2))), 2),
           sfx_cues=[{k: c[k] for k in ("t", "event", "file", "db")} for c in ex], loudnorm_in=j, border=C.get("border", False), master_lufs=MASTER_I, true_peak_db=MASTER_TP)
json.dump(log, open(dst + ".mix_log.json", "w"), indent=1); print(f"finished {dst}: {len(ex)} SFX, music {log['music_under_speech_db']} dB vs VO")
