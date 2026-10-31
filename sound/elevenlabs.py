"""ElevenLabs music and sound-effects calls.

The key is read from the ELEVENLABS_API_KEY environment variable. Nothing in
this module contains a key. If the variable is unset, callers should use the
local synthesizer instead.
"""
import json, os, urllib.request

API = "https://api.elevenlabs.io/v1"
MUSIC_URL = API + "/music"
EFFECT_URL = API + "/sound-generation"

def api_key():
    return os.environ.get("ELEVENLABS_API_KEY") or ""

def _post(url, payload, dest):
    key = api_key()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    with urllib.request.urlopen(req, timeout=120) as response:
        data = response.read()
    os.makedirs(os.path.dirname(os.path.abspath(dest)) or ".", exist_ok=True)
    open(dest, "wb").write(data)
    if os.path.getsize(dest) < 64:
        raise RuntimeError("provider returned an empty audio file")
    return dest

def music(prefs, dest, duration_s=15.0):
    prompt = ", ".join(str(prefs.get(k) or "") for k in ("mood", "genre", "energy") if prefs.get(k))
    tempo = prefs.get("tempo_bpm")
    if tempo:
        prompt = f"{prompt}, about {tempo} bpm".strip(", ")
    ms = int(max(3, min(120, float(duration_s))) * 1000)
    return _post(MUSIC_URL, {"prompt": prompt or "instrumental bed", "music_length_ms": ms}, dest)

def effect(moment, prefs, dest, duration_s=1.5):
    mood = prefs.get("mood") or "neutral"
    text = f"{moment} sound, {mood}, short, no voice"
    return _post(EFFECT_URL, {"text": text, "duration_seconds": float(duration_s)}, dest)
