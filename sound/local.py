"""Procedural music bed and effects. No network and no API key.

The sounds are simple on purpose: a soft tonal bed at the requested tempo
and short noises for the moments the profile names. They exist so a project
can render before anyone adds a provider key.
"""
import hashlib, os, wave
import numpy as np

SR = 48000

def write_wav(path, samples, sr=SR):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    pcm = np.clip(np.asarray(samples, dtype=np.float64), -1, 1)
    ints = (pcm * 32767).astype(np.int16)
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(ints.tobytes())
    return path

def _rng(prefs, salt):
    blob = json_key(prefs) + "|" + salt
    seed = int(hashlib.sha256(blob.encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)

def json_key(prefs):
    import json
    return json.dumps(prefs, sort_keys=True, default=str)

def bed(prefs, path, duration_s=8.0):
    """A quiet tonal bed. Tempo and energy change the pulse, not a borrowed song."""
    tempo = max(60, min(180, int(prefs.get("tempo_bpm") or 90)))
    energy = str(prefs.get("energy") or "low")
    gain = {"low": 0.08, "medium": 0.14, "high": 0.22}.get(energy, 0.1)
    intensity = float(prefs.get("intensity") or 0.35)
    n = int(SR * duration_s)
    t = np.arange(n) / SR
    root = 110.0 * (1 + (tempo - 90) / 400)
    tone = np.sin(2 * np.pi * root * t)
    fifth = 0.35 * np.sin(2 * np.pi * root * 1.5 * t)
    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * (tempo / 60.0) * t)
    noise = _rng(prefs, "bed").standard_normal(n) * 0.04 * intensity
    env = np.minimum(1, t / 0.4) * np.minimum(1, (duration_s - t) / 0.6)
    samples = (tone + fifth) * pulse * gain * env + noise * env
    return write_wav(path, samples)

def effect(moment, prefs, path, duration_s=0.35):
    """One short effect named by the moment (cut, text, transition, or anything else)."""
    n = int(SR * duration_s)
    rng = _rng(prefs, moment)
    t = np.arange(n) / SR
    kind = moment.lower()
    if kind in ("text", "tick", "type"):
        sig = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 28)
    elif kind in ("transition", "whoosh"):
        freq = np.linspace(400, 1800, n)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        sig = np.sin(phase) * np.sin(np.pi * t / duration_s) * 0.5
    else:
        sig = rng.standard_normal(n) * np.exp(-t * 10) * np.sin(np.pi * np.clip(t / duration_s, 0, 1))
    return write_wav(path, sig * 0.45)
